from datetime import datetime, timezone
from uuid import UUID, uuid4
from uuid import uuid4

from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import text

from src.api.deps import SessionDep
from src.core.logging import get_logger
from src.models import (
    StagingRequest,
    StagingResponse,
)
from src.models.integrity_link import IntegrityLink
from src.services.airflow_client import get_dag_run_api
from src.core.callback import build_callback_url


# Use uvicorn's logger to get colored output
logger = get_logger()
router = APIRouter(prefix="/ingestion/staging", tags=["Ingestion", "Staging"])


def _generate_staging_table_name(dag_run_id: str) -> str:
    """Generate a unique, readable staging table name from an Airflow DAG run ID.

    Args:
        dag_run_id: The Airflow DAG run ID

    Returns:
        A unique staging table name
    """
    # TODO: could be nice to have more readable names (extract filename if possible)
    # HttpURL: Head request ?
    # FileUrl: use path name directly ?

    # Generate short hash for uniqueness (encode the full URL)
    return f"staging_{dag_run_id.replace('-', '_')[:32]}"


@router.post(
    "/",
    response_model=StagingResponse,
    summary="Submit data for staging import",
    description="Submit data for staging import by triggering the Airflow staging DAG.",
)
def staging_import(
    request: StagingRequest,
    session: SessionDep,
    sec_username: str = Header(..., alias="sec-username"),
    sec_org: str = Header(..., alias="sec-org"),
) -> StagingResponse:
    """
    Submit data for staging import.

    Args:
        request: Import configuration including type and optional URL
        sec_username: Username from geOrchestra security headers
        sec_org: Organization from geOrchestra security headers

    Returns:
        StagingResponse with DAG ID, DAG run ID, and current status
    """

    dag_run_id = str(uuid4())
    staging_table_name = _generate_staging_table_name(dag_run_id)

    # Create IntegrityLink immediately
    integrity_link = IntegrityLink(
        integrity_owner=sec_username,
        integrity_organization=sec_org,
        staging_table_name=staging_table_name,
    )
    session.add(integrity_link)
    session.commit()
    session.refresh(integrity_link)

    # Build callback parameters
    callback_params = {
        "integrity_link_id": str(integrity_link.id),
        "staging_table_name": staging_table_name,
    }

    # Build callback URLs
    success_callback_url = build_callback_url("/import/dag_success", callback_params)
    failure_callback_url = build_callback_url("/import/dag_failure", callback_params)

    logger.info(
        f"Created IntegrityLink {integrity_link.id} for DAG run {dag_run_id} | "
        f"owner={sec_username} | org={sec_org} | table={staging_table_name}"
    )
    logger.info(f"Success callback URL: {success_callback_url}")

    logger.info(f"Triggering staging_dag with source_type: {request.type.value.upper()}")

    try:
        dag_run_response = get_dag_run_api().trigger_dag_run(
            dag_id="staging_dag",
            trigger_dag_run_post_body=TriggerDAGRunPostBody(
                dag_run_id=dag_run_id,
                conf={
                    "source": str(request.url),
                    "source_type": request.type.value.upper(),
                    "staging_table_name": staging_table_name,
                    "success_callback_url": success_callback_url,
                    "failure_callback_url": failure_callback_url,
                },
            ),
        )

        return StagingResponse(
            dag_id=dag_run_response.dag_id,
            dag_run_id=dag_run_response.dag_run_id,
            status=dag_run_response.state,
            staging_table_name=staging_table_name,
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
