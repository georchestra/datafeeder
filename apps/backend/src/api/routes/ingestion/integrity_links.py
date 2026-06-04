from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import Column, MetaData, String, Table, exists, or_
from sqlalchemy import select as sa_select
from sqlmodel import Session

from src.api.deps import (
    DatafeederSessionDep,
    DataSessionDep,
    GeorchestraContextDep,
    GroupIdsDep,
)
from src.core.config import get_data_schema, get_settings, get_staging_schema
from src.core.logging import get_logger
from src.core.security import build_access_expr
from src.models.data_import import ImportType, IntegrityLinkListItem, IntegrityLinkListResponse
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import IntegrityLinkRule, RuleType
from src.models.recurrence import RecurrencePreset
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


def _check_staging_existence(rows: Sequence[Any], data_session: Session) -> set[str]:
    staging_candidates = {lnk.staging_table_name for lnk, _ in rows if lnk.staging_table_name}
    if not staging_candidates:
        return set()
    return set(
        data_session.execute(  # type: ignore[reportDeprecated]
            sa_select(_info_tables.c.table_name).where(
                _info_tables.c.table_schema == get_staging_schema(),
                _info_tables.c.table_name.in_(staging_candidates),
            )
        )
        .scalars()
        .all()
    )


def _check_final_existence(rows: Sequence[Any], data_session: Session) -> set[tuple[str, str]]:
    # Group final candidates by their target schema (org-specific or shared "data").
    # A single query per distinct schema avoids cross-schema false positives.
    final_candidates_by_schema: dict[str, set[str]] = {}
    for lnk, _ in rows:
        if lnk.final_table_name:
            schema = get_data_schema(lnk.integrity_organization)
            final_candidates_by_schema.setdefault(schema, set()).add(lnk.final_table_name)

    existing: set[tuple[str, str]] = set()
    for schema, table_names in final_candidates_by_schema.items():
        found = (
            data_session.execute(  # type: ignore[reportDeprecated]
                sa_select(_info_tables.c.table_name).where(
                    _info_tables.c.table_schema == schema,
                    _info_tables.c.table_name.in_(table_names),
                )
            )
            .scalars()
            .all()
        )
        existing.update((schema, name) for name in found)
    return existing


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
    #
    # Performance note: each chunk issues queries per distinct schema. If most integrity_links
    # have orphaned tables (staging/final dropped), many chunks may be scanned before accumulating
    # BATCH_SIZE items. On large instances this can become expensive. A future improvement would
    # be to increase the chunk size beyond BATCH_SIZE+1 or hard-cap the total rows scanned.
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

        # Check table existence against data_engine's DB (correct DB in all modes).
        # Using data_session ensures information_schema reflects datadb, not georchestra.
        # Raw Table objects require execute(); exec() only accepts SQLModel SelectOfScalar.
        staging_tables = _check_staging_existence(rows, data_session)
        existing_final = _check_final_existence(rows, data_session)

        def _final_exists(lnk: IntegrityLink) -> bool:
            if not lnk.final_table_name:
                return False
            return (
                get_data_schema(lnk.integrity_organization),
                lnk.final_table_name,
            ) in existing_final

        for i, (link, access_level) in enumerate(rows):
            if (
                link.source_import_type == ImportType.EMPTY
                or (link.staging_table_name and link.staging_table_name in staging_tables)
                or _final_exists(link)
            ):
                accumulated.append((link, access_level, _final_exists(link), fetch_offset + i))

        if last_chunk_len < BATCH_SIZE + 1:
            break  # DB exhausted
        fetch_offset += last_chunk_len

    # Total rows scanned = completed chunks + final (possibly partial) chunk.
    # Warn when significantly more rows were scanned than returned — a sign that many
    # integrity_links have orphaned staging/final tables and cleanup may be needed.
    rows_scanned = fetch_offset - offset + last_chunk_len
    if rows_scanned > BATCH_SIZE * 3:
        logger.warning(
            f"Integrity-link list scanned {rows_scanned} DB rows to fill one page "
            f"(user='{geo_ctx.username}', offset={offset}). "
            "Many links may have orphaned staging/final tables — consider cleanup."
        )

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
        item.preset_id = RecurrencePreset.from_cron(link.schedule) if link.schedule else None
        items.append(item)

    link_uuids = [UUID(item.id) for item in items]
    rules_with_links: set[UUID] = set(
        session.execute(  # type: ignore[reportDeprecated]
            sa_select(IntegrityLinkRule.integrity_link_id)  # type: ignore[reportArgumentType]
            .where(IntegrityLinkRule.integrity_link_id.in_(link_uuids))  # type: ignore[union-attr]
            .distinct()
        )
        .scalars()
        .all()
    )
    for item in items:
        item.has_integrity_rules = UUID(item.id) in rules_with_links

    usernames = list({item.integrity_owner for item in items})
    display_names = ConsoleService(get_settings().CONSOLE_INTERNAL_URL).fetch_users_by_usernames(usernames)
    for item in items:
        item.owner_display_name = display_names.get(item.integrity_owner)

    return IntegrityLinkListResponse(
        items=items,
        has_more=has_more,
        offset=offset,
        next_offset=next_offset,
    )
