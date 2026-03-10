from fastapi import APIRouter, Query
from sqlmodel import select

from src.api.deps import DatafeederSessionDep, GeorchestraContextDep
from src.core.logging import get_logger
from src.models.data_import import IntegrityLinkListItem, IntegrityLinkListResponse
from src.models.integrity_link import IntegrityLink

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
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    offset: int = Query(0, ge=0, description="Number of items to skip (for lazy loading)"),
    search: str | None = Query(None, description="Filter by integrity title (case-insensitive)"),
) -> IntegrityLinkListResponse:
    """
    List integrity links with role-based access control.

    - Normal users see only their own integrity links (integrity_owner == username)
    - Administrators see all integrity links

    Args:
        session: Database session (injected)
        geo_ctx: geOrchestra security context with username and roles
        offset: Number of items to skip for pagination (lazy loading)

    Returns:
        IntegrityLinkListResponse with items, has_more flag, and current offset
    """
    is_admin = geo_ctx.is_administrator()

    # Build query based on user role
    query = select(IntegrityLink)

    if not is_admin:
        # Non-admins only see their own integrity links
        query = query.where(IntegrityLink.integrity_owner == geo_ctx.username)

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

    return IntegrityLinkListResponse(
        items=[IntegrityLinkListItem.model_validate(link) for link in items],
        has_more=has_more,
        offset=offset,
    )
