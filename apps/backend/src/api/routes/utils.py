from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from src.api.deps import SessionDep
from src.core.config import settings
from src.models.integrity_link import IntegrityLink
from src.services.geoserver import GeoServerService

router = APIRouter(prefix="/utils", tags=["utils"])


class DatasetBroadcastRequest(BaseModel):
    id: UUID


class BroadcastResponse(BaseModel):
    integrity_link: IntegrityLink
    geoserver_workspace: dict


@router.get("/health-check/")
async def health_check() -> bool:
    return True


@router.post("/temp/dataset/broadcast", response_model=BroadcastResponse)
async def broadcast_dataset(session: SessionDep, request: DatasetBroadcastRequest):
    """
    Broadcast dataset by retrieving IntegrityLink from database and creating a GeoServer workspace.
    """
    statement = select(IntegrityLink).where(IntegrityLink.id == request.id)
    integrity_link = session.exec(statement).first()

    if not integrity_link:
        raise HTTPException(status_code=404, detail=f"IntegrityLink with id {request.id} not found")

    # Create workspace in GeoServer through the gateway
    geoserver_service = GeoServerService(
        base_url=settings.GEOSERVER_URL,
        username=settings.GEOSERVER_USER,
        password=settings.GEOSERVER_PASSWORD,
    )

    # Use organization name as workspace name, organization_name_ds as datastore
    workspace_name = integrity_link.integrity_organization
    datastore_name = f"{workspace_name}_ds"

    try:
        workspace = await geoserver_service.create_workspace(
            workspace_name=workspace_name, datastore_name=datastore_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create GeoServer workspace: {str(e)}"
        )

    return BroadcastResponse(integrity_link=integrity_link, geoserver_workspace=workspace)
