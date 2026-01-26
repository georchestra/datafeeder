from fastapi import APIRouter, Header, Query
from sqlmodel import select

from src.api.deps import DatakernSessionDep
from src.core.logging import get_logger
from src.models.data_import import IntegrityLinkListItem, IntegrityLinkListResponse
from src.models.integrity_link import IntegrityLink

router = APIRouter(prefix="/ingestion/integrity-links", tags=["Ingestion"])
logger = get_logger()

BATCH_SIZE = 100  # Fixed batch size for lazy loading


def has_administrator_role(sec_roles: str) -> bool:
    """
    Check if the user has the ADMINISTRATOR role.

    Args:
        sec_roles: Semicolon-separated roles from geOrchestra gateway

    Returns:
        True if user has ADMINISTRATOR role, False otherwise
    """
    if not sec_roles:
        return False
    roles = {role.strip().upper() for role in sec_roles.split(";") if role.strip()}
    return "ADMINISTRATOR" in roles


@router.get(
    "/",
    response_model=IntegrityLinkListResponse,
    summary="List integrity links",
    description="List integrity links with role-based filtering. "
    "Normal users see only their own links, administrators see all links.",
)
def list_integrity_links(
    session: DatakernSessionDep,
    sec_username: str = Header(..., alias="sec-username", include_in_schema=False),
    sec_roles: str = Header("", alias="sec-roles", include_in_schema=False),
    offset: int = Query(0, ge=0, description="Number of items to skip (for lazy loading)"),
) -> IntegrityLinkListResponse:
    """
    List integrity links with role-based access control.

    - Normal users see only their own integrity links (integrity_owner == sec_username)
    - Administrators see all integrity links

    Args:
        session: Database session (injected)
        sec_username: Username from geOrchestra security headers
        sec_roles: Roles from geOrchestra security headers (semicolon-separated)
        offset: Number of items to skip for pagination (lazy loading)

    Returns:
        IntegrityLinkListResponse with items, has_more flag, and current offset
    """
    is_admin = has_administrator_role(sec_roles)

    # Build query based on user role
    query = select(IntegrityLink)

    if not is_admin:
        # Non-admins only see their own integrity links
        query = query.where(IntegrityLink.integrity_owner == sec_username)

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
        f"Listed {len(items)} integrity links for user '{sec_username}' "
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
