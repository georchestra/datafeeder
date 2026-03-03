from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import Column, MetaData, String, Table, exists, literal, or_
from sqlalchemy import select as sa_select

from src.api.deps import DatafeederSessionDep, GeorchestraContextDep, OrgIdDep
from src.core.config import get_staging_schema
from src.core.logging import get_logger
from src.core.security import build_access_expr
from src.models.data_import import IntegrityLinkListItem, IntegrityLinkListResponse
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import IntegrityLinkRule, RuleType

router = APIRouter(prefix="/ingestion/integrity-links", tags=["Ingestion"])
logger = get_logger()

BATCH_SIZE = 100  # Fixed batch size for lazy loading

_info_tables = Table(
    "tables",
    MetaData(schema="information_schema"),
    Column("table_schema", String),
    Column("table_name", String),
)


@router.get(
    "/",
    response_model=IntegrityLinkListResponse,
    summary="List integrity links",
    description="List integrity links with role-based filtering. "
    "Normal users see only their own links, administrators see all links.",
)
def list_integrity_links(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    org_id: OrgIdDep,
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
        geo_ctx: geOrchestra security context with username and roles
        offset: Number of items to skip for pagination (lazy loading)

    Returns:
        IntegrityLinkListResponse with items, has_more flag, and current offset
    """
    is_admin = geo_ctx.is_administrator()

    _il = IntegrityLink.__table__  # type: ignore[reportAttributeAccessIssue]

    staging_exists = (
        sa_select(literal(1))
        .select_from(_info_tables)
        .where(_info_tables.c.table_schema == get_staging_schema())
        .where(_info_tables.c.table_name == _il.c.staging_table_name)  # type: ignore[union-attr]
        .correlate(_il)  # type: ignore[arg-type]
        .exists()
    )

    final_exists = (
        sa_select(literal(1))
        .select_from(_info_tables)
        .where(_info_tables.c.table_schema == "data")
        .where(_info_tables.c.table_name == _il.c.final_table_name)  # type: ignore[union-attr]
        .correlate(_il)  # type: ignore[arg-type]
        .exists()
    )

    access_expr = build_access_expr(geo_ctx.username, org_id, is_admin)
    query = sa_select(
        IntegrityLink,
        access_expr.label("access_level"),
        final_exists.label("has_final_table"),
    ).where(or_(staging_exists, final_exists))

    if not is_admin:
        # Non-admins see: own datasets + datasets with METADATA rules for their org
        conditions: list[Any] = [IntegrityLink.integrity_owner == geo_ctx.username]
        if org_id:
            conditions.append(
                exists(
                    sa_select(IntegrityLinkRule.id).where(  # type: ignore[reportArgumentType]
                        IntegrityLinkRule.integrity_link_id == IntegrityLink.id,
                        IntegrityLinkRule.rule_type == RuleType.METADATA,
                        IntegrityLinkRule.group_or_role == org_id,
                    )
                )
            )
        query = query.where(or_(*conditions))

    # Apply search filter if provided
    if search:
        query = query.where(IntegrityLink.integrity_title.ilike(f"%{search}%"))  # type: ignore[union-attr]

    query = query.order_by(IntegrityLink.created_at.desc())  # type: ignore[union-attr]
    query = query.offset(offset).limit(BATCH_SIZE + 1)

    rows = session.execute(query).all()  # type: ignore[reportDeprecated]
    has_more = len(rows) > BATCH_SIZE
    items_rows = rows[:BATCH_SIZE]

    logger.info(
        f"Listed {len(items_rows)} integrity links for user '{geo_ctx.username}' "
        f"(admin={is_admin}, offset={offset}, has_more={has_more}, search={search!r})"
    )

    items: list[IntegrityLinkListItem] = []
    for link, access_level, has_final in items_rows:
        item = IntegrityLinkListItem.model_validate(link)
        item.access_level = access_level
        item.has_final_table = bool(has_final)
        items.append(item)

    return IntegrityLinkListResponse(
        items=items,
        has_more=has_more,
        offset=offset,
    )
