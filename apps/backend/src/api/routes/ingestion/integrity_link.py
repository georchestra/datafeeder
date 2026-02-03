from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.api.deps import DatakernSessionDep
from src.models.data_import import IntegrityLinkResponse
from src.models.integrity_link import IntegrityLink

router = APIRouter(prefix="/ingestion/integrity-link", tags=["Ingestion"])


@router.get(
    "/{integrity_link_id}",
    response_model=IntegrityLinkResponse,
    summary="Get IntegrityLink by ID",
    description="Retrieve an IntegrityLink entity. The integrity_transformation field is excluded by default.",
)
def get_integrity_link(
    session: DatakernSessionDep,
    integrity_link_id: str,
    include_transformation: bool = Query(
        False,
        description="Include the integrity_transformation field in the response",
    ),
) -> IntegrityLinkResponse:
    """Get an IntegrityLink entity by its ID."""
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    response = IntegrityLinkResponse.model_validate(integrity_link)

    if not include_transformation:
        response.integrity_transformation = None

    return response
