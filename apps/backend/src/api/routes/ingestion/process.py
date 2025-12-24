from datetime import datetime, timezone
from uuid import UUID, uuid4

from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from data_manipulation.utils import sanitize_name
from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import MetaData, Table

from src.api.deps import SessionDep
from src.core.callback import build_callback_url
from src.core.config import get_settings
from src.core.logging import get_logger
from src.models import (
    ProcessRequest,
    ProcessResponse,
)
from src.models.integrity_link import IntegrityLink
from src.services.airflow_client import get_dag_run_api
from src.services.console_service import ConsoleService
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
    session: SessionDep,
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

    dag_run_id = str(uuid4())
    final_table_name = sanitize_name(request.title) + "_" + dag_run_id.replace("-", "_")[:32]

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
def dag_success_callback(
    session: SessionDep,
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

        metadata_id = metadata_service.create_and_publish_metadata(
            integrity_link,
            user_email=contact_email,
            user_first_name=user_first_name,
            user_last_name=user_last_name,
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
def dag_failure_callback(
    session: SessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    final_table_name: str = Query(None, description="Final table name (if created)"),
) -> None:
    """
    Failure callback endpoint called by Airflow DAG on failure.
    Drops the final table if it exists and marks the IntegrityLink as failed.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        final_table_name: Final table name (optional, in case it was partially created)

    Returns:
        Success message with cleanup details
    """
    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Drop the final table if it exists
    try:
        schema = "data"  # FIXME get it from config
        metadata = MetaData(schema=schema)
        table = Table(final_table_name, metadata)
        table.drop(session.get_bind(), checkfirst=True)
        session.commit()
    except Exception as e:
        # Log the error but continue with IntegrityLink deletion
        logger.error(f"Error dropping final table {final_table_name}: {e}")

    # Mark the integrity link as failed (keep it for auditing purposes)
    # TODO: Add a status field to IntegrityLink model to track failures
    # For now, we just log the failure
    logger.error(
        f"Process DAG failure for IntegrityLink {integrity_link.id} | "
        f"final_table={integrity_link.final_table_name}"
    )
