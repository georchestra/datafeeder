from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from src.api.deps import DatakernSessionDep, GeorchestraContextDep
from src.models.data_import import IntegrityLinkResponse
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import IntegrityLinkRule

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


@router.get(
    "/{integrity_link_id}/rules",
    response_model=list[IntegrityLinkRule],
    summary="List rules for an IntegrityLink",
    description="Retrieve all rules associated with a given IntegrityLink.",
)
def list_integrity_link_rules(
    session: DatakernSessionDep,
    georchestra_context: GeorchestraContextDep,
    integrity_link_id: str,
) -> list[IntegrityLinkRule]:
    """List all rules for a given IntegrityLink."""
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    statement = select(IntegrityLinkRule).where(
        IntegrityLinkRule.integrity_link_id == UUID(integrity_link_id)
    )
    return list(session.exec(statement).all())
