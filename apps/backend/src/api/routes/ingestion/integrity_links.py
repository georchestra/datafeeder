from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import Column, MetaData, String, Table, exists, or_
from sqlalchemy import select as sa_select
from sqlmodel import Session

from src.api.deps import DatafeederSessionDep, DataSessionDep, GeorchestraContextDep, GroupIdsDep, OrgIdDep
from src.core.config import get_staging_schema, get_settings
from src.core.logging import get_logger
from src.core.security import build_access_expr
from src.models.data_import import IntegrityLinkListItem, IntegrityLinkListResponse
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import IntegrityLinkRule, RuleType
from src.services.console_service import ConsoleService

router = APIRouter(prefix="/ingestion/integrity-links", tags=["Ingestion"])
logger = get_logger()

BATCH_SIZE = 100  # Fixed batch size for lazy loading

_info_tables = Table(
    "tables",
    MetaData(schema="information_schema"),
    Column("table_schema", String),
    Column("table_name", String),
)


def _check_table_existence(rows: list[Any], data_session: Session) -> tuple[set[str], set[str]]:
    staging_candidates = {lnk.staging_table_name for lnk, _ in rows if lnk.staging_table_name}
    final_candidates = {lnk.final_table_name for lnk, _ in rows if lnk.final_table_name}

    staging_tables: set[str] = (
        set(
            data_session.execute(  # type: ignore[reportDeprecated]
                sa_select(_info_tables.c.table_name).where(
                    _info_tables.c.table_schema == get_staging_schema(),
                    _info_tables.c.table_name.in_(staging_candidates),
                )
            )
            .scalars()
            .all()
        )
        if staging_candidates
        else set()
    )
    final_tables: set[str] = (
        set(
            data_session.execute(  # type: ignore[reportDeprecated]
                sa_select(_info_tables.c.table_name).where(
                    _info_tables.c.table_schema == "data",
                    _info_tables.c.table_name.in_(final_candidates),
                )
            )
            .scalars()
            .all()
        )
        if final_candidates
        else set()
    )
    return staging_tables, final_tables


@router.get(
    "/",
    response_model=IntegrityLinkListResponse,
    summary="List integrity links",
    description="List integrity links with role-based filtering. "
    "Normal users see only their own links, administrators see all links.",
)
def list_integrity_links(
    session: DatafeederSessionDep,
    data_session: DataSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
    offset: int = Query(0, ge=0, description="Number of items to skip (for lazy loading)"),
    search: str | None = Query(None, description="Filter by integrity title (case-insensitive)"),
) -> IntegrityLinkListResponse:
    """
    List integrity links with role-based access control.

    - Administrators see all integrity links
    - Owners see their own integrity links
    - Users see datasets where their organization has a METADATA permission rule

    Args:
        session: Database session (injected)
        data_session: Data engine session for table existence checks (injected)
        geo_ctx: geOrchestra security context with username and roles
        offset: Number of items to skip for pagination (lazy loading)

    Returns:
        IntegrityLinkListResponse with items, has_more flag, and current offset
    """
    is_admin = geo_ctx.is_administrator()

    access_expr = build_access_expr(geo_ctx.username, group_ids, is_admin)
    query = sa_select(IntegrityLink, access_expr.label("access_level"))

    if not is_admin:
        # Non-admins see: own datasets + datasets with METADATA rules matching any
        # of the user's group identifiers (org UUID in ORG mode, role UUIDs in ROLE mode).
        conditions: list[Any] = [IntegrityLink.integrity_owner == geo_ctx.username]
        if group_ids:
            conditions.append(
                exists(
                    sa_select(IntegrityLinkRule.id).where(  # type: ignore[reportArgumentType]
                        IntegrityLinkRule.integrity_link_id == IntegrityLink.id,
                        IntegrityLinkRule.rule_type == RuleType.METADATA,
                        IntegrityLinkRule.group_or_role.in_(group_ids),  # type: ignore[attr-defined]
                    )
                )
            )
        query = query.where(or_(*conditions))

    # Apply search filter if provided
    if search:
        query = query.where(IntegrityLink.integrity_title.ilike(f"%{search}%"))  # type: ignore[union-attr]

    base_query = query.order_by(IntegrityLink.created_at.desc())  # type: ignore[union-attr]

    # Fetch in chunks until BATCH_SIZE+1 filtered items accumulated or DB exhausted.
    # Needed because table-existence filtering happens post-query (cross-DB information_schema
    # check), so a simple limit(BATCH_SIZE+1) can produce a false has_more=False.
    # Each item carries its raw DB row index so next_offset is exact, not estimated.
    accumulated: list[tuple[IntegrityLink, Any, bool, int]] = []
    fetch_offset = offset
    last_chunk_len = 0

    while len(accumulated) < BATCH_SIZE + 1:
        rows = session.execute(  # type: ignore[reportDeprecated]
            base_query.offset(fetch_offset).limit(BATCH_SIZE + 1)
        ).all()
        last_chunk_len = len(rows)
        if not rows:
            break

        staging_tables, final_tables = _check_table_existence(rows, data_session)

        for i, (link, access_level) in enumerate(rows):
            if (link.staging_table_name and link.staging_table_name in staging_tables) or (
                link.final_table_name and link.final_table_name in final_tables
            ):
                has_final = bool(link.final_table_name and link.final_table_name in final_tables)
                accumulated.append((link, access_level, has_final, fetch_offset + i))

        if last_chunk_len < BATCH_SIZE + 1:
            break  # DB exhausted
        fetch_offset += last_chunk_len

    has_more = len(accumulated) > BATCH_SIZE
    items_rows = accumulated[:BATCH_SIZE]
    next_offset = accumulated[BATCH_SIZE][3] if has_more else fetch_offset + last_chunk_len

    logger.info(
        f"Listed {len(items_rows)} integrity links for user '{geo_ctx.username}' "
        f"(admin={is_admin}, offset={offset}, has_more={has_more}, search={search!r})"
    )

    items: list[IntegrityLinkListItem] = []
    for link, access_level, has_final, _ in items_rows:
        item = IntegrityLinkListItem.model_validate(link)
        item.access_level = access_level
        item.has_final_table = bool(has_final)
        items.append(item)

    usernames = list({item.integrity_owner for item in items})
    display_names = ConsoleService(get_settings().CONSOLE_URL).fetch_users_by_usernames(usernames)
    for item in items:
        item.owner_display_name = display_names.get(item.integrity_owner)

    return IntegrityLinkListResponse(
        items=items,
        has_more=has_more,
        offset=offset,
        next_offset=next_offset,
    )
