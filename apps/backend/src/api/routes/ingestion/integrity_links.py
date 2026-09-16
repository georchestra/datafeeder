from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import Column, MetaData, String, Table, and_, case, exists, or_
from sqlalchemy import select as sa_select
from sqlmodel import Session, col

from src.api.deps import (
    DatafeederSessionDep,
    DataSessionDep,
    GeorchestraContextDep,
    GroupIdsDep,
)
from src.api.routes.groups_common import GroupItem
from src.core.config import get_data_schema, get_settings, get_staging_schema
from src.core.logging import get_logger
from src.core.security import (
    AccessLevel,
    build_access_expr,
    load_authorized_integrity_link,
    visibility_condition,
)
from src.models.data_import import (
    ImportType,
    IntegrityLinkListItem,
    IntegrityLinkListResponse,
    JoinableColumn,
    JoinableTable,
    PublicAccess,
)
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import IntegrityLinkRule
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

_info_columns = Table(
    "columns",
    MetaData(schema="information_schema"),
    Column("table_schema", String),
    Column("table_name", String),
    Column("column_name", String),
)


def _check_staging_existence(rows: Sequence[Any], data_session: Session) -> set[str]:
    staging_candidates = {lnk.staging_table_name for lnk, *_ in rows if lnk.staging_table_name}
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
    for lnk, *_ in rows:
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


# Any IntegrityLinkRule row counts, unlike build_access_expr's caller-scoped subquery.
_rule_exists = exists(
    sa_select(col(IntegrityLinkRule.id)).where(
        col(IntegrityLinkRule.integrity_link_id) == IntegrityLink.id
    )
)
_gn = col(IntegrityLink.gn_is_published)
_gs = col(IntegrityLink.gs_is_published)
_public_access_expr = case(
    (and_(_gn, _gs), PublicAccess.OPEN.value),
    (or_(_gn, _gs, _rule_exists), PublicAccess.RESTRICTED.value),
    else_=PublicAccess.UNCONFIGURED.value,
)


@router.get(
    "/",
    response_model=IntegrityLinkListResponse,
    summary="List integrity links",
    description="List integrity links with role-based filtering. "
    "Normal users see only their own links, administrators see all links. "
    "Supports filtering by title search, public access level, and recurrence preset "
    "(AND across filters, OR within a filter's multiple values).",
)
def list_integrity_links(
    session: DatafeederSessionDep,
    data_session: DataSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
    offset: int = Query(0, ge=0, description="Number of items to skip (for lazy loading)"),
    search: str | None = Query(None, description="Filter by integrity title (case-insensitive)"),
    access: Annotated[
        list[PublicAccess] | None, Query(description="Filter by public access level")
    ] = None,
    recurrence: Annotated[
        list[RecurrencePreset] | None, Query(description="Filter by recurrence preset")
    ] = None,
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
        search: Case-insensitive substring match on integrity_title
        access: Public access levels to include (OR'd together)
        recurrence: Recurrence presets to include (OR'd together)

    Returns:
        IntegrityLinkListResponse with items, has_more flag, and current offset
    """
    is_admin = geo_ctx.is_administrator()

    access_expr = build_access_expr(geo_ctx.username, group_ids, is_admin)
    query = sa_select(
        IntegrityLink,
        access_expr.label("access_level"),
        _rule_exists.label("has_integrity_rules"),
        _public_access_expr.label("public_access"),
    )

    if not is_admin:
        # Non-admins see: own datasets + datasets with METADATA rules matching any
        # of the user's group identifiers (org UUID in ORG mode, role UUIDs in ROLE mode).
        query = query.where(visibility_condition(geo_ctx.username, group_ids))

    # Apply search filter if provided
    if search:
        query = query.where(IntegrityLink.integrity_title.ilike(f"%{search}%"))  # type: ignore[union-attr]
    if access:
        query = query.where(_public_access_expr.in_([level.value for level in access]))
    if recurrence:
        query = query.where(IntegrityLink.schedule.in_([preset.cron for preset in recurrence]))  # type: ignore[union-attr]

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
    accumulated: list[tuple[Any, bool, int]] = []
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

        for i, row in enumerate(rows):
            link = row[0]
            if (
                link.source_import_type in (ImportType.EMPTY, ImportType.PREFILLED)
                or (link.staging_table_name and link.staging_table_name in staging_tables)
                or _final_exists(link)
            ):
                accumulated.append((row, _final_exists(link), fetch_offset + i))

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
    next_offset = accumulated[BATCH_SIZE][2] if has_more else fetch_offset + last_chunk_len

    logger.info(
        f"Listed {len(items_rows)} integrity links for user '{geo_ctx.username}' "
        f"(admin={is_admin}, offset={offset}, has_more={has_more}, search={search!r})"
    )

    items: list[IntegrityLinkListItem] = []
    for (link, access_level, has_rules, public_access), has_final, _ in items_rows:
        item = IntegrityLinkListItem.model_validate(link)
        item.access_level = access_level
        item.has_final_table = bool(has_final)
        item.preset_id = RecurrencePreset.from_cron(link.schedule) if link.schedule else None
        item.has_integrity_rules = bool(has_rules)
        item.public_access = PublicAccess(public_access)
        items.append(item)

    usernames = list({item.integrity_owner for item in items})
    display_names = ConsoleService(get_settings().CONSOLE_INTERNAL_URL).fetch_users_by_usernames(
        usernames
    )
    for item in items:
        item.owner_display_name = display_names.get(item.integrity_owner)

    return IntegrityLinkListResponse(
        items=items,
        has_more=has_more,
        offset=offset,
        next_offset=next_offset,
    )


@router.get(
    "/organizations",
    response_model=list[GroupItem],
    summary="List distinct organizations across accessible integrity links",
    description="Distinct integrity_organization values across integrity links the caller "
    "can see, paired with their console long name for display in a filter dropdown.",
)
def list_integrity_link_organizations(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
) -> list[GroupItem]:
    """List distinct organizations, restricted to datasets the caller can see."""
    query = sa_select(col(IntegrityLink.integrity_organization)).distinct()
    if not geo_ctx.is_administrator():
        query = query.where(visibility_condition(geo_ctx.username, group_ids))

    short_names = session.execute(query).scalars().all()  # type: ignore[reportDeprecated]
    if not short_names:
        return []

    try:
        organizations = ConsoleService(get_settings().CONSOLE_INTERNAL_URL).get_all_organizations()
        long_names = {
            org["shortName"]: org["name"]
            for org in organizations
            if org.get("shortName") and org.get("name")
        }
    except Exception as e:
        logger.warning(f"Failed to fetch organizations from console: {e}", exc_info=True)
        long_names = {}

    return [
        GroupItem(id=short_name, label=long_names.get(short_name, short_name))
        for short_name in sorted(short_names)
    ]


@router.get(
    "/owners",
    response_model=list[GroupItem],
    summary="List distinct owners across accessible integrity links",
    description="Distinct integrity_owner values across integrity links the caller can see, "
    "paired with their console display name for display in a filter dropdown.",
)
def list_integrity_link_owners(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
) -> list[GroupItem]:
    """List distinct owners, restricted to datasets the caller can see."""
    query = sa_select(col(IntegrityLink.integrity_owner)).distinct()
    if not geo_ctx.is_administrator():
        query = query.where(visibility_condition(geo_ctx.username, group_ids))

    usernames = session.execute(query).scalars().all()  # type: ignore[reportDeprecated]
    if not usernames:
        return []

    display_names = ConsoleService(get_settings().CONSOLE_INTERNAL_URL).fetch_users_by_usernames(
        list(usernames)
    )
    return [
        GroupItem(id=username, label=display_names.get(username) or username)
        for username in sorted(usernames)
    ]


@router.get(
    "/joinable-tables",
    response_model=list[JoinableTable],
    summary="List tables available for join",
    description="List tables available for join with role-based filtering. "
    "Normal users see only their own links, administrators see all links. "
    "No filtering on COPY mode or reference datasets yet.",
)
def list_joinable_tables(
    session: DatafeederSessionDep,
    data_session: DataSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
) -> list[JoinableTable]:
    """List tables available as join targets, restricted to datasets the caller can see."""
    query = sa_select(IntegrityLink).where(col(IntegrityLink.final_table_name).is_not(None))

    if not geo_ctx.is_administrator():
        # Same visibility rule as the main integrity-links list: own datasets +
        # datasets with a METADATA rule matching the user's org/role — a user
        # shouldn't be able to discover table/column names of datasets they
        # otherwise have no access to.
        query = query.where(visibility_condition(geo_ctx.username, group_ids))

    links = session.execute(query).scalars().all()  # type: ignore[reportDeprecated]

    existing_final = _check_final_existence([(lnk, None) for lnk in links], data_session)

    return [
        JoinableTable(
            id=lnk.id,
            integrity_title=lnk.integrity_title,
            table_name=lnk.final_table_name,
        )
        for lnk in links
        if (get_data_schema(lnk.integrity_organization), lnk.final_table_name) in existing_final
    ]


@router.get(
    "/{integrity_link_id}/joinable-columns",
    response_model=list[JoinableColumn],
    summary="List the columns of a joinable table",
)
def get_joinable_columns(
    integrity_link_id: UUID,
    session: DatafeederSessionDep,
    data_session: DataSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
) -> list[JoinableColumn]:
    """List the columns of a joinable table; 404/403 mirror load_authorized_integrity_link."""
    link, _ = load_authorized_integrity_link(
        str(integrity_link_id), AccessLevel.METADATA_READ, geo_ctx, session, group_ids
    )
    if not link.final_table_name:
        raise HTTPException(status_code=404, detail="IntegrityLink has no final table yet")

    schema = get_data_schema(link.integrity_organization)
    column_names = (
        data_session.execute(  # type: ignore[reportDeprecated]
            sa_select(_info_columns.c.column_name).where(
                _info_columns.c.table_schema == schema,
                _info_columns.c.table_name == link.final_table_name,
            )
        )
        .scalars()
        .all()
    )

    return [JoinableColumn(column_name=name) for name in column_names]
