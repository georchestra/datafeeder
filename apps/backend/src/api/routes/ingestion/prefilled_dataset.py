from fastapi import APIRouter
from pydantic import BaseModel

from src.api.deps import DatafeederSessionDep, GeorchestraContextDep
from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.data_import import ImportType, IntegrityLinkResponse
from src.models.integrity_link import IntegrityLink
from src.services.metadata_service import MetadataService

router = APIRouter(prefix="/ingestion/integrity-link", tags=["Ingestion"])
logger = get_logger()


class CreatePrefilledDatasetRequest(BaseModel):
    data_id: str
    metadata_id: str


@router.post(
    "/prefilled",
    response_model=IntegrityLinkResponse,
    status_code=201,
    summary="Create a prefilled dataset integrity link",
    description=(
        "Create an integrity link referencing data and metadata that already exist. "
        "The title is fetched from the GeoNetwork record identified by metadata_id. "
        "No staging, processing DAG, or metadata publication is triggered. "
        "Recurrence scheduling and event logs are not available for this type."
    ),
)
def create_prefilled_dataset(
    request: CreatePrefilledDatasetRequest,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
) -> IntegrityLinkResponse:
    settings = get_settings()

    metadata_service = MetadataService(
        gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
        datadir_path=settings.DATADIR_PATH,
        credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
        gn_sync_mode=settings.GN_SYNC_MODE,
        verify_tls=False,
    )
    title = metadata_service.get_title(request.metadata_id) or "Untitled Dataset"

    integrity_link = IntegrityLink(
        integrity_owner=geo_ctx.username,
        integrity_organization=geo_ctx.organization,
        source_import_type=ImportType.PREFILLED if request.data_id else ImportType.EMPTY,
        integrity_title=title,
        data_id=request.data_id,
        metadata_id=request.metadata_id,
    )
    session.add(integrity_link)
    session.commit()
    session.refresh(integrity_link)

    logger.info(
        "Created %s integrity link %s (data_id=%s, metadata_id=%s)",
        ImportType.PREFILLED if request.data_id else ImportType.EMPTY,
        integrity_link.id,
        request.data_id,
        request.metadata_id,
    )

    return IntegrityLinkResponse.model_validate(integrity_link)
