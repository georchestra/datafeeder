from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import (
    ConsoleServiceDep,
    DatafeederSessionDep,
    GeorchestraContextDep,
    MetadataServiceDep,
)
from src.core.logging import get_logger
from src.models.data_import import ImportType, IntegrityLinkResponse
from src.models.integrity_link import IntegrityLink
from src.services.metadata_publication import publish_new_record

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
    metadata_service: MetadataServiceDep,
    console_service: ConsoleServiceDep,
) -> IntegrityLinkResponse:
    title = request.title.strip() if request.title else "Untitled Dataset"

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
        # No layer_urls → no online resources in the metadata record
        publish_new_record(metadata_service, console_service, integrity_link, geo_ctx)
    except Exception as e:
        logger.error(
            "Failed to publish metadata for empty dataset %s: %s",
            integrity_link.id,
            e,
            exc_info=True,
        )
        session.rollback()
        raise HTTPException(status_code=500, detail="import.metadataPublication.error")

    session.commit()
    session.refresh(integrity_link)

    return IntegrityLinkResponse.model_validate(integrity_link)
