from datetime import datetime, timezone
from uuid import UUID

from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN
from data_manipulation.database import create_schema, get_available_table_name
from data_manipulation.utils import sanitize_name
from data_manipulation.validators import validate_table_name
from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import MetaData, Table, func, select

from src.api.deps import DatakernSessionDep, DataSessionDep
from src.core.callback import build_callback_url
from src.core.config import get_settings, get_staging_schema
from src.core.db import data_engine
from src.core.logging import get_logger
from src.models import (
    ProcessRequest,
    ProcessResponse,
)
from src.models.integrity_link import IntegrityLink
from src.services.airflow_client import get_dag_run_api
from src.services.console_service import ConsoleService
from src.services.geoserver import GeoServerService  # type: ignore[attr-defined]
from src.services.metadata_service import MetadataService

router = APIRouter(prefix="/ingestion/process", tags=["Ingestion"])
logger = get_logger()
settings = get_settings()


@router.post(
    "/",
    response_model=ProcessResponse,
    summary="Submit staging data for processing",
    description="Submit staging data for processing by triggering the Airflow process DAG.",
)
async def process_staging_data(
    request: ProcessRequest,
    session: DatakernSessionDep,
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
        sec_username: Username from geOrchestra security headers

    Returns:
        StagingResponse with integrity link ID, DAG ID, DAG run ID, and current DAG run status
    """

    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(request.integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Check ownership
    if integrity_link.integrity_owner != sec_username:
        raise HTTPException(status_code=403, detail="User does not own the IntegrityLink")

    # Get staging table name from IntegrityLink
    staging_table_name = integrity_link.staging_table_name
    if not staging_table_name:
        raise HTTPException(status_code=400, detail="Staging table name not found in IntegrityLink")

    dag_run_id = f"{integrity_link.id}_{int(datetime.now(timezone.utc).timestamp())}_manual"
    final_table_name = get_available_table_name(
        data_engine, "data", sanitize_name(request.title)[:53]
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
        logger.error(f"Generated invalid final table name from title '{request.title}': {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Title produces invalid table name: {e}",
        )

    # Set integrity_title (raw request.title)
    integrity_link.integrity_title = request.title

    # --- Prepare layer URLs and GeoNetwork metadata ---
    workspace_name = integrity_link.integrity_organization.lower()

    # Determine if staging table has geometry (to pre-compute correct URLs)
    try:
        staging_meta = MetaData(schema=get_staging_schema())
        staging_tbl = Table(staging_table_name, staging_meta, autoload_with=data_engine)
        is_geographic = DEFAULT_GEOMETRY_COLUMN in staging_tbl.c
    except Exception:
        is_geographic = False

    # Compute layer URLs — pure string building, no GeoServer API call
    geoserver_service = GeoServerService(
        base_url=settings.GEOSERVER_URL,
        username=settings.GEOSERVER_USER,
        password=settings.GEOSERVER_PASSWORD,
        public_url=settings.DATA_PUBLIC_URL,
    )
    layer_urls = geoserver_service.build_layer_urls(
        workspace_name=workspace_name,
        table_name=final_table_name,
        is_geographic=is_geographic,
    )

    # Create and publish metadata to GeoNetwork — fatal on failure
    try:
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
            detail="Failed to publish metadata. Please try again later.",
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
        dag_run_response = get_dag_run_api().trigger_dag_run(
            dag_id="process_dag",
            trigger_dag_run_post_body=TriggerDAGRunPostBody(
                dag_run_id=dag_run_id,
                conf={
                    "staging_table_name": staging_table_name,
                    "final_table_name": final_table_name,
                    "integrity_transformation": integrity_link.integrity_transformation or {},
                    "success_callback_url": success_callback_url,
                    "failure_callback_url": failure_callback_url,
                },
            ),
        )

        return ProcessResponse(
            integrity_link_id=request.integrity_link_id,
            dag_id=dag_run_response.dag_id,
            dag_run_id=dag_run_response.dag_run_id,
            status=dag_run_response.state,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.post("/dag_success")
async def dag_success_callback(
    datakern_session: DatakernSessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    final_table_name: str = Query(..., description="Final table name"),
) -> None:
    """
    Success callback endpoint called by Airflow DAG on successful completion.
    Creates the GeoServer workspace/datastore/layer with the actual bbox now that the table exists.

    Args:
        datakern_session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        final_table_name: Final table name created by the process DAG
    """
    integrity_link = datakern_session.get(IntegrityLink, UUID(integrity_link_id))
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
        geoserver_service = GeoServerService(
            base_url=settings.GEOSERVER_URL,
            username=settings.GEOSERVER_USER,
            password=settings.GEOSERVER_PASSWORD,
            public_url=settings.DATA_PUBLIC_URL,
        )

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
        bbox = ""

        if is_geographic:
            stmt = select(func.ST_Extent(table.c[DEFAULT_GEOMETRY_COLUMN]))
            with data_engine.connect() as conn:
                result = conn.execute(stmt).scalar_one_or_none()
            bbox = str(result) if result else ""

        await geoserver_service.create_layer(
            workspace_name=workspace_name,
            datastore_name=datastore_name,
            table_name=final_table_name,
            title=integrity_link.integrity_title or final_table_name,
            abstract=integrity_link.integrity_title or final_table_name,
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
    integrity_link.last_retrieval_timestamp = datetime.now(timezone.utc)

    datakern_session.commit()
    datakern_session.refresh(integrity_link)

    logger.info(
        f"Process DAG success for IntegrityLink {integrity_link.id} | "
        f"final_table={final_table_name}"
    )


@router.post("/dag_failure")
async def dag_failure_callback(
    data_session: DataSessionDep,
    datakern_session: DatakernSessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    final_table_name: str = Query(None, description="Final table name (if created)"),
) -> None:
    """
    Failure callback endpoint called by Airflow DAG on failure.
    Drops the final table if it exists and marks the IntegrityLink as failed.

    Args:
        data_session: Data database session (injected)
        datakern_session: Datakern database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        final_table_name: Final table name (optional, in case it was partially created)

    Returns:
        Success message with cleanup details
    """
    # Query existing IntegrityLink
    integrity_link = datakern_session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Drop the final table if it exists
    if final_table_name:
        try:
            # CRITICAL: Validate table name before using in SQL (defense in depth)
            from data_manipulation.validators import validate_table_name

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
