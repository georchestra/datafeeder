from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import DatafeederSessionDep, GeorchestraContextDep
from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.data_import import ImportType, IntegrityLinkResponse
from src.models.integrity_link import IntegrityLink
from src.services.console_service import ConsoleService
from src.services.metadata_service import MetadataService

router = APIRouter(prefix="/ingestion/integrity-link", tags=["Ingestion"])
logger = get_logger()


class CreateEmptyDatasetRequest(BaseModel):
    title: str | None = None


@router.post(
    "/empty",
    response_model=IntegrityLinkResponse,
    status_code=201,
    summary="Create an empty dataset",
    description=(
        "Create an integrity link without any source data. "
        "A GeoNetwork metadata record is created immediately (no online resources). "
        "No staging or processing DAG is triggered."
    ),
)
def create_empty_dataset(
    request: CreateEmptyDatasetRequest,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
) -> IntegrityLinkResponse:
    title = request.title.strip() if request.title else "Untitled Dataset"
    settings = get_settings()

    integrity_link = IntegrityLink(
        integrity_owner=geo_ctx.username,
        integrity_organization=geo_ctx.organization,
        source_import_type=ImportType.EMPTY,
        integrity_title=title,
    )
    session.add(integrity_link)
    session.flush()
    session.refresh(integrity_link)

    try:
        console_service = ConsoleService(settings.CONSOLE_INTERNAL_URL)
        organization = console_service.get_organization(geo_ctx.organization)

        if organization:
            contact_email = organization.get("mail") or geo_ctx.email
            org_name = organization.get("name")
            user_first_name = org_name or geo_ctx.firstname
            user_last_name = "" if org_name else geo_ctx.lastname
        else:
            contact_email = geo_ctx.email
            user_first_name = geo_ctx.firstname
            user_last_name = geo_ctx.lastname

        metadata_service = MetadataService(
            gn_api_url=f"{settings.GEONETWORK_URL}/srv/api",
            datadir_path=settings.DATADIR_PATH,
            credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
            gn_sync_mode=settings.GN_SYNC_MODE,
            verify_tls=False,
        )

        # No layer_urls → no online resources in the metadata record
        metadata_service.create_and_publish_metadata(
            integrity_link,
            user_email=contact_email,
            user_first_name=user_first_name,
            user_last_name=user_last_name,
        )
        integrity_link.metadata_id = str(integrity_link.id)
        logger.info("Metadata published for empty dataset %s", integrity_link.id)
    except Exception as e:
        logger.error(
            "Failed to publish metadata for empty dataset %s: %s",
            integrity_link.id,
            e,
            exc_info=True,
        )
        session.rollback()
        raise HTTPException(status_code=500, detail="import.metadataPublication.error")

    # Ownership — soft failure
    try:
        metadata_service.set_record_ownership(
            metadata_uuid=str(integrity_link.id),
            username=integrity_link.integrity_owner,
            group_name=integrity_link.integrity_organization,
        )
    except Exception as e:
        logger.warning("Failed to set metadata ownership for %s: %s", integrity_link.id, e)

    session.commit()
    session.refresh(integrity_link)

    return IntegrityLinkResponse.model_validate(integrity_link)
