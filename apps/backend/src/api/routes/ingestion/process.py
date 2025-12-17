from datetime import datetime, timezone
from uuid import UUID, uuid4
from uuid import uuid4

from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import text

from src.api.deps import SessionDep
from src.core.config import get_settings
from src.core.logging import get_logger
from src.models import (
    ProcessRequest,
    ProcessResponse,
)
from src.models.integrity_link import IntegrityLink
from src.services.airflow_client import get_dag_run_api
from src.core.callback import build_callback_url
from data_manipulation.utils import sanitize_name

router = APIRouter(prefix="/ingestion/process", tags=["Ingestion", "Process"])
logger = get_logger()
settings = get_settings()


@router.post(
    "/",
    response_model=ProcessResponse,
    summary="Submit staging data for processing",
    description="Submit staging data for final processing by triggering the Airflow final DAG.",
)
def final_import(request: ProcessRequest) -> ProcessResponse:
    """
    Submit staging data for processing.

    Args:
        request: Final import configuration including staging table name and final table name
    
    Returns:
        ProcessResponse with DAG ID, DAG run ID, and current status
    """

    dag_run_id = str(uuid4())
    final_table_name = sanitize_name(request.title) + "_" + dag_run_id.replace('-', '_')[:32]
    
    # integrity_transformation = request.config # TODO: use it

    # TODO: update integrity link with integrity_title (raw request.title) and integrity_transformation
    # -> json is too big to be passed as params to airflow

    callback_params = {
        "integrity_link_id": str(uuid4()),
        "staging_table_name": request.staging_table_name,
    }
    
    # Build callback URLs
    success_callback_url = build_callback_url("/import/dag_success", callback_params)
    failure_callback_url = build_callback_url("/import/dag_failure", callback_params)

    try:
        dag_run_response = get_dag_run_api().trigger_dag_run(
            dag_id="process_dag",
            trigger_dag_run_post_body=TriggerDAGRunPostBody(
                dag_run_id=dag_run_id,
                conf={
                    "staging_table_name": request.staging_table_name,
                    "final_table_name": final_table_name,
                    "success_callback_url": success_callback_url,
                    "failure_callback_url": failure_callback_url,
                },
            ),
        )

        return ProcessResponse(
            dag_id=dag_run_response.dag_id,
            dag_run_id=dag_run_response.dag_run_id,
            status=dag_run_response.state,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.post("/dag_success", tags=["Callbacks"])
def dag_success_callback(
    session: SessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    staging_table_name: str = Query(..., max_length=63, description="Staging table name"),
):
    """
    Success callback endpoint called by Airflow DAG on successful completion.
    Updates the existing IntegrityLink record with job duration.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        staging_table_name: Staging table name (required, max 63 chars, for verification)

    Returns:
        Success message with updated IntegrityLink details
    """
    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Verify staging table name matches
    if integrity_link.staging_table_name != staging_table_name:
        raise HTTPException(
            status_code=400,
            detail=f"Staging table name mismatch: expected {integrity_link.staging_table_name}, got {staging_table_name}",
        )

    # Calculate job duration
    now = datetime.now(timezone.utc)

    # Ensure created_at exists and is timezone-aware
    if integrity_link.created_at is None:
        raise HTTPException(
            status_code=500,
            detail="IntegrityLink created_at is missing",
        )

    created_at = (
        integrity_link.created_at.replace(tzinfo=timezone.utc)
        if integrity_link.created_at.tzinfo is None
        else integrity_link.created_at
    )
    retrieve_time = now - created_at

    # Update IntegrityLink
    integrity_link.retrieve_time = retrieve_time
    integrity_link.last_staging_retrieved_at = now
    session.commit()
    session.refresh(integrity_link)

    return {
        "message": "DAG success callback processed",
        "integrity_link_id": str(integrity_link.id),
        "owner": integrity_link.integrity_owner,
        "organization": integrity_link.integrity_organization,
        "staging_table_name": integrity_link.staging_table_name,
        "retrieve_time_seconds": retrieve_time.total_seconds(),
    }


@router.post("/dag_failure", tags=["Callbacks"])
def dag_failure_callback(
    session: SessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    staging_table_name: str = Query(..., max_length=63, description="Staging table name"),
):
    """
    Failure callback endpoint called by Airflow DAG on failure.
    Deletes the IntegrityLink and drops the staging table.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        staging_table_name: Staging table name to drop (required, max 63 chars)

    Returns:
        Success message with cleanup details
    """
    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Verify staging table name matches
    if integrity_link.staging_table_name != staging_table_name:
        raise HTTPException(
            status_code=400,
            detail=f"Staging table name mismatch: expected {integrity_link.staging_table_name}, got {staging_table_name}",
        )

    # Drop the staging table if it exists
    # Use parameterized query with identifier to prevent SQL injection
    try:
        # Validate table name format (alphanumeric and underscores only)
        if not staging_table_name.replace("_", "").isalnum():
            raise ValueError(f"Invalid table name format: {staging_table_name}")

        # Use quoted identifier for safety
        # Note: execute() is correct here for DDL statements (not deprecated for this use case)
        schema = "data"  # FIXME get from config
        session.execute(text(f'DROP TABLE IF EXISTS "{schema}"."{staging_table_name}" CASCADE'))  # type: ignore[misc]
        session.commit()
    except Exception as e:
        # Log the error but continue with IntegrityLink deletion
        logger.error(f"Error dropping staging table {staging_table_name}: {e}")

    # Delete the IntegrityLink
    session.delete(integrity_link)
    session.commit()

    return {
        "message": "DAG failure callback processed",
        "integrity_link_id": str(integrity_link_id),
        "staging_table_name": staging_table_name,
        "actions": ["staging_table_dropped", "integrity_link_deleted"],
    }
