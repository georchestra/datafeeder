from datetime import datetime, timezone
from uuid import UUID

from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from data_manipulation.database import create_schema
from data_manipulation.utils import sanitize_name
from data_manipulation.validators import validate_table_name
from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import MetaData, Table

from src.api.deps import DatakernSessionDep, DataSessionDep
from src.core.callback import build_callback_url
from src.core.config import get_settings
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
def process_staging_data(
    request: ProcessRequest,
    session: DatakernSessionDep,
    sec_username: str = Header(..., alias="sec-username", include_in_schema=False),
    sec_email: str = Header("", alias="sec-email", include_in_schema=False),
    sec_firstname: str = Header("", alias="sec-firstname", include_in_schema=False),
    sec_lastname: str = Header("", alias="sec-lastname", include_in_schema=False),
) -> ProcessResponse:
    """
    Submit staging data for processing.

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
    final_table_name = sanitize_name(request.title)[:30] + "_" + dag_run_id.replace("-", "_")[:32]

    # Validate the generated table name (defense in depth)
    try:
        validate_table_name(final_table_name, context="final")
    except ValueError as e:
        logger.error(f"Generated invalid final table name from title '{request.title}': {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Title produces invalid table name: {e}",
        )

    # integrity_transformation = request.config # FIXME: currently not used

    # TODO: update integrity link with integrity_transformation
    # -> json is too big to be passed as params to airflow

    # Set integrity_title (raw request.title)
    integrity_link.integrity_title = request.title
    session.commit()
    session.refresh(integrity_link)

    # Build callback parameters
    callback_params = {
        "integrity_link_id": str(integrity_link.id),
        "final_table_name": final_table_name,
        "user_email": sec_email,
        "user_first_name": sec_firstname,
        "user_last_name": sec_lastname,
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
    session: DatakernSessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    final_table_name: str = Query(..., description="Final table name"),
    user_email: str = Query("", description="User email"),
    user_first_name: str = Query("", description="User first name"),
    user_last_name: str = Query("", description="User last name"),
) -> None:
    """
    Success callback endpoint called by Airflow DAG on successful completion.
    Updates the existing IntegrityLink record with final table name and retrieval timestamp.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        final_table_name: Final table name created by the process DAG

    Returns:
        Success message with updated IntegrityLink details
    """
    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Initialize layer_urls for metadata generation
    layer_urls = None

    # Publish to GeoServer (workspace, datastore, and layer)
    # This must happen BEFORE GeoNetwork publication
    try:
        # Get workspace and datastore names from IntegrityLink
        workspace_name = integrity_link.integrity_organization.lower()
        datastore_name = f"{workspace_name}_ds"

        # Create database schema first
        create_schema(data_engine, workspace_name)
        logger.info(f"Created/verified PostgreSQL schema: {workspace_name}")

        # Initialize GeoServer service
        geoserver_service = GeoServerService(
            base_url=settings.GEOSERVER_URL,
            username=settings.GEOSERVER_USER,
            password=settings.GEOSERVER_PASSWORD,
            public_url=settings.DATA_PUBLIC_URL,
        )

        # Check if GeoServer workspace and datastore already exist
        workspace_exists = await geoserver_service.workspace_exists(workspace_name)
        datastore_exists = await geoserver_service.datastore_exists(workspace_name, datastore_name)

        if not final_table_name:
            logger.info(
                f"Skipping layer creation for IntegrityLink {integrity_link.id}: "
                f"final_table_name not available"
            )
            raise Exception("final_table_name is required for GeoServer layer creation")

        if workspace_exists and datastore_exists:
            logger.info(
                f"Reusing existing GeoServer workspace and datastore for IntegrityLink {integrity_link.id}: "
                f"workspace={workspace_name}, datastore={datastore_name}"
            )
        else:
            # Create GeoServer workspace and datastore
            _workspace = await geoserver_service.create_workspace(
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                pg_schema="data",  # Point to the schema where Airflow creates final tables
            )
            logger.info(
                f"Created GeoServer workspace and datastore for IntegrityLink {integrity_link.id}: "
                f"workspace={workspace_name}, datastore={datastore_name}"
            )

        try:
            logger.info(
                f"Creating GeoServer layer for IntegrityLink {integrity_link.id}: "
                f"layer={final_table_name}"
                f"layers_urls={layer_urls}"
            )

            # Use SQLAlchemy Core to safely construct the query
            metadata = MetaData(schema="data")
            table = Table(final_table_name, metadata, autoload_with=data_engine)
            is_geographic = "geom" in table.c

            layer_urls = await geoserver_service.create_layer(
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                table_name=final_table_name,
                title=integrity_link.integrity_title or final_table_name,
                abstract=integrity_link.integrity_title or final_table_name,
                is_geographic=is_geographic,
            )
            integrity_link.data_id = workspace_name + ":" + final_table_name

            logger.info(
                f"Data published to GeoServer for IntegrityLink {integrity_link.id}: {integrity_link.data_id} | "
                f"WMS URL={layer_urls.wms.capabilities}, "
                f"WFS URL={layer_urls.wfs.capabilities}"
            )
        except Exception as layer_error:
            # Log the error but don't fail - workspace/datastore were created successfully
            logger.warning(
                f"Failed to create GeoServer layer for IntegrityLink {integrity_link.id}: "
                f"{str(layer_error)}",
                exc_info=True,
            )

    except Exception as e:
        # Soft failure - log the error but continue with the callback
        logger.error(
            f"Failed to publish to GeoServer for IntegrityLink {integrity_link.id}: {e}",
            exc_info=True,
        )
        # Continue with GeoNetwork publication and IntegrityLink update

    # Create and publish metadata to GeoNetwork
    try:
        # Try to get organization email from console API
        console_service = ConsoleService(settings.CONSOLE_URL)
        contact_email = console_service.get_organization_email(
            integrity_link.integrity_organization
        )
        # Fall back to user email if organization email not found
        if not contact_email:
            contact_email = user_email
            logger.info(
                f"Using user email for metadata contact: {user_email} "
                f"(org email not available for '{integrity_link.integrity_organization}')"
            )
        else:
            logger.info(f"Using organization email for metadata contact: {contact_email}")

        metadata_service = MetadataService(
            gn_api_url=f"{settings.GEONETWORK_URL}/srv/api",
            datadir_path=settings.DATADIR_PATH,
            credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
            verify_tls=False,
        )

        # Pass layer URLs to metadata service (if layer creation succeeded, else None)
        metadata_id = metadata_service.create_and_publish_metadata(
            integrity_link,
            user_email=contact_email,
            user_first_name=user_first_name,
            user_last_name=user_last_name,
            layer_urls=layer_urls.model_dump() if layer_urls else None,
        )
        integrity_link.metadata_id = metadata_id

        logger.info(f"Metadata published for IntegrityLink {integrity_link.id}: {metadata_id}")

    except Exception as e:
        logger.error(
            f"Failed to publish metadata for IntegrityLink {integrity_link.id}: {e}", exc_info=True
        )
        # Continue with IntegrityLink update even if metadata fails (soft failure)

    # Update IntegrityLink with final table information
    integrity_link.final_table_name = final_table_name
    integrity_link.last_retrieval_timestamp = datetime.now(timezone.utc)

    session.commit()
    session.refresh(integrity_link)

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
