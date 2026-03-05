from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import exists
from sqlmodel import or_, select

from src.api.deps import DatakernSessionDep, GeorchestraContextDep, OrgIdDep
from src.core.logging import get_logger
from src.core.security import compute_effective_access
from src.models.data_import import IntegrityLinkListItem, IntegrityLinkListResponse
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import IntegrityLinkRule, RuleType

router = APIRouter(prefix="/ingestion/integrity-links", tags=["Ingestion"])
logger = get_logger()

BATCH_SIZE = 100  # Fixed batch size for lazy loading


@router.get(
    "/",
    response_model=IntegrityLinkListResponse,
    summary="List integrity links",
    description="List integrity links with role-based filtering. "
    "Normal users see only their own links, administrators see all links.",
)
def list_integrity_links(
    session: DatakernSessionDep,
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
    # Build query based on user role
    query = select(IntegrityLink)

    is_admin = geo_ctx.is_administrator()
    if not is_admin:
        # Non-admins see: own datasets + datasets with METADATA rules for their org
        conditions: list[Any] = [IntegrityLink.integrity_owner == geo_ctx.username]
        if org_id:
            conditions.append(
                exists(
                    select(IntegrityLinkRule.id).where(
                        IntegrityLinkRule.integrity_link_id == IntegrityLink.id,
                        IntegrityLinkRule.rule_type == RuleType.METADATA,
                        IntegrityLinkRule.group_or_role == org_id,
                    )
                )
            )
        query = query.where(or_(*conditions))

    if search:
        query = query.where(IntegrityLink.integrity_title.ilike(f"%{search}%"))  # type: ignore[union-attr]

    # Order by created_at descending (newest first)
    query = query.order_by(IntegrityLink.created_at.desc())  # type: ignore[union-attr]

    # Fetch one extra item to determine if there are more items
    query = query.offset(offset).limit(BATCH_SIZE + 1)

    results = session.exec(query).all()

    # Check if there are more items
    has_more = len(results) > BATCH_SIZE

    # Only return up to BATCH_SIZE items
    items = results[:BATCH_SIZE]

    logger.info(
        f"Listed {len(items)} integrity links for user '{geo_ctx.username}' "
        f"(admin={is_admin}, offset={offset}, has_more={has_more}, search={search!r})"
    )

    # Compute per-item access level
    list_items: list[IntegrityLinkListItem] = []
    for link in items:
        effective = compute_effective_access(link, geo_ctx, session, org_id)
        if effective is None:
            logger.warning(
                f"Skipping integrity link '{link.id}' for user '{geo_ctx.username}': "
                "no effective access (possible race condition)"
            )
            continue

        item = IntegrityLinkListItem.model_validate(link)
        item.access_level = effective.value
        list_items.append(item)

    return IntegrityLinkListResponse(
        items=list_items,
        has_more=has_more,
        offset=offset,
    )
