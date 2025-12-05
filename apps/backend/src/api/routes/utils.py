from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import select

from src.api.deps import SessionDep
from src.core.config import settings
from src.models.integrity_link import IntegrityLink
from src.services.geoserver import GeoServerService  # type: ignore[attr-defined]

router = APIRouter(prefix="/utils", tags=["utils"])


class DatasetBroadcastRequest(BaseModel):
    id: UUID


class WMSUrls(BaseModel):
    capabilities: str
    getmap: str
    legend: str


class WFSUrls(BaseModel):
    capabilities: str
    getfeature: str


class GeoServerLayer(BaseModel):
    workspace: str
    datastore: str
    layer: str
    layer_qualified_name: str
    table: str
    wms: WMSUrls | None = None
    wfs: WFSUrls | None = None


class BroadcastResponse(BaseModel):
    integrity_link: IntegrityLink
    geoserver_workspace: dict[str, str]
    geoserver_layer: GeoServerLayer | None = None


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
            workspace_name=workspace_name,
            datastore_name=datastore_name,
        )
        
        # Create layer if final_table_name exists (optional - don't fail if this doesn't work)
        layer = None
        if integrity_link.final_table_name:
            try:
                layer = await geoserver_service.create_layer(
                    workspace_name=workspace_name,
                    datastore_name=datastore_name,
                    layer_name=integrity_link.final_table_name,
                    table_name=integrity_link.final_table_name,
                    title=integrity_link.final_table_name,
                )
            except Exception as layer_error:
                # Log the error but don't fail the whole request
                # The workspace/datastore were created successfully
                print(f"Warning: Failed to create layer: {str(layer_error)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create GeoServer workspace: {str(e)}"
        )

    return BroadcastResponse(
        integrity_link=integrity_link, geoserver_workspace=workspace, geoserver_layer=layer
    )
