from fastapi import APIRouter, Query
from sqlmodel import select

from src.api.deps import DatakernSessionDep, GeorchestraContextDep
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
    session: DatakernSessionDep,
    geo_ctx: GeorchestraContextDep,
    offset: int = Query(0, ge=0, description="Number of items to skip (for lazy loading)"),
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
        f"(admin={is_admin}, offset={offset}, has_more={has_more})"
    )

    return IntegrityLinkListResponse(
        items=[
            IntegrityLinkListItem(
                id=str(link.id),
                integrity_title=link.integrity_title,
                integrity_owner=link.integrity_owner,
                integrity_organization=link.integrity_organization,
                source_import_type=link.source_import_type,
                source_file_name=link.source_file_name,
                source_file_type=link.source_file_type,
                source_url=link.source_url,
                source_auth_enabled=link.source_auth_enabled,
                staging_table_name=link.staging_table_name,
                final_table_name=link.final_table_name,
                metadata_id=link.metadata_id,
                data_id=link.data_id,
                created_at=link.created_at,
                last_retrieval_timestamp=link.last_retrieval_timestamp,
                schedule=link.schedule,
                schedule_enabled=link.schedule_enabled,
            )
            for link in items
        ],
        has_more=has_more,
        offset=offset,
    )
