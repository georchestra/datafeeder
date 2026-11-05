from data_manipulation.database import read_table_extent, schema_exists, table_exists
from data_manipulation.utils import build_db_uri, sanitize_name
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import col, select

from src.api.deps import (
    DatafeederSessionDep,
    GeorchestraContextDep,
    GeoServerServiceDep,
    MetadataServiceDep,
)
from src.core.config import DirectAccessSourceDatabase, get_settings
from src.core.db import get_source_engine
from src.core.logging import get_logger
from src.models.data_import import ImportType, IntegrityLinkResponse
from src.models.integrity_link import IntegrityLink
from src.services.georchestra import GeorchestraContext
from src.services.layer_publication import publish_table
from src.services.metadata_publication import publish_new_record

router = APIRouter(prefix="/ingestion/integrity-link", tags=["Ingestion"])
logger = get_logger()


class CreateDirectAccessDatasetRequest(BaseModel):
    db_key: str = Field(min_length=1, description="Key of a direct_access SOURCE_DATABASES entry")
    schema_name: str = Field(min_length=1)
    table_name: str = Field(min_length=1)
    title: str | None = None


def _get_direct_access_database(
    db_key: str, geo_ctx: GeorchestraContext
) -> DirectAccessSourceDatabase:
    db = get_settings().SOURCE_DATABASES.get(db_key)
    if not isinstance(db, DirectAccessSourceDatabase):
        raise HTTPException(status_code=404, detail=f"Unknown direct access database '{db_key}'")
    if (
        db.roles
        and not geo_ctx.is_administrator()
        and not any(geo_ctx.has_role(role) for role in db.roles)
    ):
        raise HTTPException(status_code=403, detail="Not allowed to use this database")
    return db


@router.post(
    "/direct-access",
    response_model=IntegrityLinkResponse,
    status_code=201,
    summary="Create a direct access dataset",
    description=(
        "Publish a table of a direct_access source database in place, without copy: "
        "creates the integrity link, its GeoNetwork metadata record and its GeoServer layer, "
        "in a datastore of the organization workspace reading the table schema through the "
        "database JNDI reference. No staging or processing DAG is triggered."
    ),
)
async def create_direct_access_dataset(
    request: CreateDirectAccessDatasetRequest,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    geoserver_service: GeoServerServiceDep,
    metadata_service: MetadataServiceDep,
) -> IntegrityLinkResponse:
    db = _get_direct_access_database(request.db_key, geo_ctx)
    schema, table = request.schema_name, request.table_name

    # GeoServer names the layer and reads the table under its sanitized name
    if sanitize_name(table) != table:
        raise HTTPException(
            status_code=422,
            detail=f"Table name '{table}' cannot be published as is: "
            "lowercase letters, digits and underscores only",
        )

    engine = get_source_engine(request.db_key)
    if engine is None or not schema_exists(engine, schema):
        raise HTTPException(status_code=422, detail=f"Schema '{schema}' not found")
    if not table_exists(engine, schema, table):
        raise HTTPException(
            status_code=422, detail=f"Table '{table}' not found in schema '{schema}'"
        )

    source_url = build_db_uri(request.db_key, schema, table)
    workspace_name = geo_ctx.organization.lower()
    duplicate = session.exec(
        select(IntegrityLink.id).where(
            col(IntegrityLink.source_import_type) == ImportType.DIRECT_ACCESS,
            col(IntegrityLink.source_url) == source_url,
            col(IntegrityLink.integrity_organization) == geo_ctx.organization,
        )
    ).first()
    if duplicate is not None:
        raise HTTPException(
            status_code=409, detail=f"Table already published by dataset {duplicate}"
        )

    # Layer names are unique per workspace: another store may already publish this name
    if geoserver_service.workspace_layer_exists(workspace_name, table):
        raise HTTPException(
            status_code=409,
            detail=f"Layer '{table}' already exists in workspace '{workspace_name}'",
        )

    try:
        extent = read_table_extent(engine, schema, table)
    except Exception as e:
        logger.error("Failed to read extent of %s: %s", source_url, e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read the table extent")

    title = (request.title or "").strip() or table
    integrity_link = IntegrityLink(
        integrity_owner=geo_ctx.username,
        integrity_organization=geo_ctx.organization,
        source_import_type=ImportType.DIRECT_ACCESS,
        source_url=source_url,
        integrity_title=title,
    )
    session.add(integrity_link)
    session.flush()
    session.refresh(integrity_link)

    try:
        publish_new_record(
            metadata_service,
            integrity_link,
            geo_ctx,
            geoserver_service.build_layer_urls_for_metadata(
                workspace_name=workspace_name,
                table_name=table,
                is_geographic=extent.is_geographic,
            ),
        )
    except Exception as e:
        logger.error(
            "Failed to publish metadata for direct access dataset %s: %s",
            integrity_link.id,
            e,
            exc_info=True,
        )
        session.rollback()
        raise HTTPException(status_code=500, detail="import.metadataPublication.error")

    # One datastore per database schema in the organization workspace
    try:
        await publish_table(
            geoserver_service,
            integrity_link,
            table,
            extent,
            datastore_name=sanitize_name(f"{request.db_key}_{schema}"),
            pg_schema=schema,
            jndi_reference=db.jndi_reference,
        )
    except Exception as e:
        logger.error(
            "Failed to publish direct access dataset %s to GeoServer: %s",
            integrity_link.id,
            e,
            exc_info=True,
        )
        metadata_service.delete_record(str(integrity_link.metadata_id))
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to publish the layer to GeoServer")

    session.commit()
    session.refresh(integrity_link)

    logger.info(
        "Created direct access dataset %s: %s published as %s",
        integrity_link.id,
        source_url,
        integrity_link.data_id,
    )
    return IntegrityLinkResponse.model_validate(integrity_link)
