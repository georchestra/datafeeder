from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN
from data_manipulation.database import create_schema, get_available_table_name
from data_manipulation.models import IntegrityTransformation
from data_manipulation.utils import (
    compute_bbox_from_postgis_stextent_string,
    sanitize_name,
)
from data_manipulation.validators import validate_table_name
from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import MetaData, Table, func, select

from src.api.deps import (
    DatafeederSessionDep,
    DataSessionDep,
    GeorchestraContextDep,
    GeoServerServiceDep,
    OrgIdDep,
)
from src.core.callback import build_callback_url
from src.core.config import get_settings, get_staging_schema
from src.core.db import data_engine
from src.core.logging import get_logger
from src.core.security import AccessLevel, load_authorized_integrity_link
from src.models import (
    ProcessRequest,
    ProcessResponse,
)
from src.models.integrity_link import IntegrityLink
from src.services.console_service import ConsoleService
from src.services.executor_factory import get_task_executor
from src.services.metadata_service import MetadataService

router = APIRouter(prefix="/ingestion/process", tags=["Ingestion"])
logger = get_logger()
settings = get_settings()


def _is_geom_excluded(transformation: dict[str, Any] | None) -> bool:
    """Return True when the geometry column is explicitly excluded in the transformation config."""
    if not transformation:
        return False
    parsed = IntegrityTransformation.model_validate(transformation)
    return parsed.columns is not None and any(
        col.original_name == DEFAULT_GEOMETRY_COLUMN and col.excluded for col in parsed.columns
    )


def _normalize_title(raw: str | None, fallback: str = "No title") -> str:
    """Strip whitespace from title; return fallback when the result is empty."""
    if raw is not None:
        stripped = raw.strip()
        if stripped:
            return stripped
    return fallback


@router.post(
    "/",
    response_model=ProcessResponse,
    summary="Submit staging data for processing",
    description="Submit staging data for processing by triggering the Airflow process DAG.",
)
def process_staging_data(
    request: ProcessRequest,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    org_id: OrgIdDep,
    geoserver_service: GeoServerServiceDep,
    sec_username: str = Header(..., alias="sec-username", include_in_schema=False),
    sec_email: str = Header("", alias="sec-email", include_in_schema=False),
    sec_firstname: str = Header("", alias="sec-firstname", include_in_schema=False),
    sec_lastname: str = Header("", alias="sec-lastname", include_in_schema=False),
) -> ProcessResponse:
    """
    Submit staging data for processing.

    Creates GeoNetwork metadata immediately using pre-computed layer URLs, then triggers the
    Airflow DAG. GeoServer workspace/datastore/layer creation happens in dag_success_callback
    once the final table exists and the actual bbox can be computed.

    Args:
        request: Process configuration including integrity link ID and title
        geo_ctx: geOrchestra security context

    Returns:
        StagingResponse with integrity link ID, DAG ID, DAG run ID, and current DAG run status
    """

    # Load IntegrityLink and verify OWNER_ONLY permission (owner or admin)
    integrity_link, _ = load_authorized_integrity_link(
        request.integrity_link_id, AccessLevel.OWNER_ONLY, geo_ctx, session, org_id
    )

    # Get staging table name from IntegrityLink
    staging_table_name = integrity_link.staging_table_name
    if not staging_table_name:
        raise HTTPException(status_code=400, detail="Staging table name not found in IntegrityLink")

    title = _normalize_title(request.title)
    dag_run_id = f"{integrity_link.id}_{int(datetime.now(timezone.utc).timestamp())}_manual"
    final_table_name = (
        integrity_link.final_table_name
        if integrity_link.last_retrieval_timestamp is not None
        else get_available_table_name(data_engine, "data", sanitize_name(title))
    )
    if not final_table_name:
        raise HTTPException(
            status_code=400,
            detail="Could not generate unique final table name",
        )

    # Validate the generated table name (defense in depth)
    try:
        validate_table_name(final_table_name, context="final")
    except ValueError as e:
        logger.error(f"Generated invalid final table name from title '{title}': {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Title produces invalid table name: {e}",
        )

    # Set integrity_title
    integrity_link.integrity_title = title

    # Apply recurrence schedule if provided, or clear it
    if request.recurrence is not None:
        integrity_link.schedule = request.recurrence.cron
        integrity_link.schedule_enabled = True
        logger.info(
            f"Recurrence set for IntegrityLink {integrity_link.id}: "
            f"{request.recurrence} → {request.recurrence.cron}"
        )
    else:
        integrity_link.schedule = None
        integrity_link.schedule_enabled = False

    # --- Prepare layer URLs and GeoNetwork metadata ---
    workspace_name = integrity_link.integrity_organization.lower()

    # Determine if staging table has geometry (to pre-compute correct URLs)
    try:
        staging_meta = MetaData(schema=get_staging_schema())
        staging_tbl = Table(staging_table_name, staging_meta, autoload_with=data_engine)
        is_geographic = DEFAULT_GEOMETRY_COLUMN in staging_tbl.c and not _is_geom_excluded(
            integrity_link.integrity_transformation
        )
    except Exception:
        is_geographic = False

    # Create and publish metadata to GeoNetwork, only if metadata_id is not already set (first time process, not re-run)
    if integrity_link.metadata_id is None:
        try:
            # Compute layer URLs — pure string building, no GeoServer API call
            layer_urls = geoserver_service.build_layer_urls_for_metadata(
                workspace_name=workspace_name,
                table_name=final_table_name,
                is_geographic=is_geographic,
            )

            console_service = ConsoleService(settings.CONSOLE_URL)
            organization = console_service.get_organization(integrity_link.integrity_organization)

            user_first_name = sec_firstname
            user_last_name = sec_lastname
            contact_email = sec_email
            if organization:
                contact_email = organization.get("mail") or sec_email
                org_name = organization.get("name")
                if org_name:
                    user_first_name = org_name
                    user_last_name = ""
                    logger.info(f"Using organization name for metadata contact: {org_name}")
            else:
                logger.info("Organization not found, using user info for metadata contact")

            metadata_service = MetadataService(
                gn_api_url=f"{settings.GEONETWORK_URL}/srv/api",
                datadir_path=settings.DATADIR_PATH,
                credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
                gn_sync_mode=settings.GN_SYNC_MODE,
                verify_tls=False,
            )

            metadata_id = metadata_service.create_and_publish_metadata(
                integrity_link,
                user_email=contact_email,
                user_first_name=user_first_name,
                user_last_name=user_last_name,
                layer_urls=layer_urls,
            )
            integrity_link.metadata_id = str(integrity_link.id)
            logger.info(f"Metadata published for IntegrityLink {integrity_link.id}: {metadata_id}")
        except Exception as e:
            logger.error(
                f"Failed to publish metadata for IntegrityLink {integrity_link.id}: {e}",
                exc_info=True,
            )
            raise HTTPException(
                status_code=500,
                detail="import.metadataPublication.error",
            )

        # Ownership assignment — soft failure (non-critical)
        try:
            metadata_service.set_record_ownership(
                metadata_uuid=str(integrity_link.id),
                username=integrity_link.integrity_owner,
                group_name=integrity_link.integrity_organization,
            )
        except Exception as ownership_error:
            logger.warning(
                "Failed to set metadata ownership for IntegrityLink %s: %s",
                integrity_link.id,
                ownership_error,
                exc_info=True,
            )

    # Persist all changes before triggering the DAG
    integrity_link.final_table_name = final_table_name
    session.commit()
    session.refresh(integrity_link)

    # Build callback parameters (no user info needed — metadata already created)
    callback_params = {
        "integrity_link_id": str(integrity_link.id),
        "final_table_name": final_table_name,
    }

    # Build callback URLs
    success_callback_url = build_callback_url("/ingestion/process/dag_success", callback_params)
    failure_callback_url = build_callback_url("/ingestion/process/dag_failure", callback_params)

    try:
        executor = get_task_executor()
        task_info = executor.trigger_process_task(
            run_id=dag_run_id,
            staging_table_name=staging_table_name,
            final_table_name=final_table_name,
            integrity_transformation=integrity_link.integrity_transformation or {},
            success_callback_url=success_callback_url,
            failure_callback_url=failure_callback_url,
            last_retrieval_timestamp=integrity_link.last_retrieval_timestamp,
        )

        return ProcessResponse(
            integrity_link_id=request.integrity_link_id,
            dag_id=task_info.task_id,
            dag_run_id=task_info.run_id,
            status=task_info.status,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task execution error: {e}")


@router.post("/dag_success")
async def dag_success_callback(
    datafeeder_session: DatafeederSessionDep,
    geoserver_service: GeoServerServiceDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    final_table_name: str = Query(..., description="Final table name"),
) -> None:
    """
    Success callback endpoint called by Airflow DAG on successful completion.
    Creates the GeoServer workspace/datastore/layer with the actual bbox now that the table exists.

    Args:
        datafeeder_session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        final_table_name: Final table name created by the process DAG
    """
    integrity_link = datafeeder_session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    workspace_name = integrity_link.integrity_organization.lower()
    datastore_name = f"{workspace_name}_ds"

    # Create PostgreSQL schema (idempotent)
    try:
        create_schema(data_engine, workspace_name)
        logger.info(f"Created/verified PostgreSQL schema: {workspace_name}")
    except Exception as e:
        logger.error(
            f"Failed to create schema for IntegrityLink {integrity_link.id}: {e}", exc_info=True
        )

    # Create GeoServer workspace, datastore, and layer with actual bbox
    try:
        workspace_exists = await geoserver_service.workspace_exists(workspace_name)
        datastore_exists = await geoserver_service.datastore_exists(workspace_name, datastore_name)

        if workspace_exists and datastore_exists:
            logger.info(
                f"Reusing existing GeoServer workspace and datastore for IntegrityLink {integrity_link.id}: "
                f"workspace={workspace_name}, datastore={datastore_name}"
            )
        else:
            await geoserver_service.create_workspace(
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                pg_schema="data",
            )
            logger.info(
                f"Created GeoServer workspace and datastore for IntegrityLink {integrity_link.id}: "
                f"workspace={workspace_name}, datastore={datastore_name}"
            )

        # Load final table, check geometry, compute bbox
        table_meta = MetaData(schema="data")
        table = Table(final_table_name, table_meta, autoload_with=data_engine)
        is_geographic = DEFAULT_GEOMETRY_COLUMN in table.c
        bbox = {"minx": -1.0, "miny": -1.0, "maxx": 0.0, "maxy": 0.0}
        epsg = None

        if is_geographic:
            with data_engine.connect() as conn:
                geom = table.c[DEFAULT_GEOMETRY_COLUMN]
                # Get SRID from PostGIS geometry column
                srid_stmt = select(func.ST_SRID(geom)).limit(1)
                srid_result = conn.execute(srid_stmt).scalar_one_or_none()
                epsg = srid_result if srid_result else None

                # Get bounding box
                bbox_stmt = select(func.ST_Extent(geom))
                bbox_result = conn.execute(bbox_stmt).scalar_one_or_none()
                if bbox_result:
                    bbox = compute_bbox_from_postgis_stextent_string(bbox_result)

        await geoserver_service.create_layer(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=final_table_name,
            title=integrity_link.integrity_title or final_table_name,
            abstract=integrity_link.integrity_title or final_table_name,
            epsg=epsg or 4326,
            is_geographic=is_geographic,
            bbox=bbox,
        )
        integrity_link.data_id = workspace_name + ":" + final_table_name
        logger.info(
            f"Created GeoServer layer for IntegrityLink {integrity_link.id}: "
            f"{integrity_link.data_id}, geographic={is_geographic}, bbox={bbox}"
        )

    except Exception as e:
        logger.error(
            f"Failed to publish to GeoServer for IntegrityLink {integrity_link.id}: {e}",
            exc_info=True,
        )

    # Update retrieval timestamp
    integrity_link.final_table_name = final_table_name
    integrity_link.last_retrieval_timestamp = datetime.now(timezone.utc)

    datafeeder_session.commit()
    datafeeder_session.refresh(integrity_link)

    # Update revision date in GeoNetwork metadata (soft failure)
    if integrity_link.metadata_id is not None:
        try:
            metadata_service = MetadataService(
                gn_api_url=f"{settings.GEONETWORK_URL}/srv/api",
                datadir_path=settings.DATADIR_PATH,
                credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
                verify_tls=False,
            )
            metadata_service.update_revision_date(
                str(integrity_link.id), datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.warning(
                "Failed to update revision date for IntegrityLink %s: %s",
                integrity_link.id,
                e,
                exc_info=True,
            )

    logger.info(
        f"Process DAG success for IntegrityLink {integrity_link.id} | "
        f"final_table={final_table_name}"
    )


@router.post("/dag_failure")
async def dag_failure_callback(
    data_session: DataSessionDep,
    datafeeder_session: DatafeederSessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    final_table_name: str = Query(None, description="Final table name (if created)"),
) -> None:
    """
    Failure callback endpoint called by Airflow DAG on failure.
    Drops the final table if it exists and marks the IntegrityLink as failed.

    Args:
        data_session: Data database session (injected)
        datafeeder_session: Datafeeder database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        final_table_name: Final table name (optional, in case it was partially created)

    Returns:
        Success message with cleanup details
    """
    # Query existing IntegrityLink
    integrity_link = datafeeder_session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Drop the final table if it exists
    if final_table_name:
        try:
            # CRITICAL: Validate table name before using in SQL (defense in depth)
            validate_table_name(final_table_name, context="final")

            schema = "data"  # FIXME get it from config
            metadata = MetaData(schema=schema)
            table = Table(final_table_name, metadata)
            table.drop(data_session.get_bind(), checkfirst=True)
            data_session.commit()
        except ValueError as e:
            # Log validation error but continue with cleanup
            logger.error(f"Invalid table name in callback: {e}")
        except Exception as e:
            # Log the error but continue with IntegrityLink deletion
            logger.error(f"Error dropping final table {final_table_name}: {e}")

    # Mark the integrity link as failed (keep it for auditing purposes)
    # TODO: Add a status field to IntegrityLink model to track failures
    # For now, we just log the failure
    logger.error(
        f"Process DAG failure for IntegrityLink {integrity_link.id} | "
        f"final_table={final_table_name}"
    )
