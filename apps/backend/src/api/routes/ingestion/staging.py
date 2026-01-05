from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy import MetaData, Table

from src.api.deps import SessionDep
from src.core.callback import build_callback_url
from src.core.logging import get_logger
from src.models import (
    StagingResponse,
)
from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.services.airflow_client import get_dag_run_api
from src.services.files import get_temp_file_url, upload_file_to_temp

# Use uvicorn's logger to get colored output
logger = get_logger()
router = APIRouter(prefix="/ingestion/staging", tags=["Ingestion"])


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
async def submit_staging(
    session: SessionDep,
    type: ImportType = Form(...),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    sec_username: str = Header(..., alias="sec-username", include_in_schema=False),
    sec_org: str = Header(..., alias="sec-org", include_in_schema=False),
) -> StagingResponse:
    """
    Submit data for staging import.

    You can test this endpoint using curl:
        curl -v --request POST   --url http://localhost:8080/datakern-backend/ingestion/staging/   --header 'Content-Type: multipart/form-data'   --form 'type=file'   --form 'file=@submarine_cable_geo.json'   --form 'name=myfiletable' --user "testadmin:testadmin"

    Args:
        request: Import configuration including type and optional URL
        sec_username: Username from geOrchestra security headers
        sec_org: Organization from geOrchestra security headers

    Returns:
        StagingResponse with integrity link ID, DAG ID, DAG run ID, and current DAG run status
    """

    dag_run_id = str(uuid4())
    staging_table_name = _generate_staging_table_name(dag_run_id)

    # Extract source according to import type
    if type == ImportType.FILE:
        if file is None:
            raise HTTPException(status_code=400, detail="File is required")        
        file_name = await upload_file_to_temp(file)
        source = get_temp_file_url(file_name)
    else:
        source = url

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
    }

    # Build callback URLs
    success_callback_url = build_callback_url("/ingestion/staging/dag_success", callback_params)
    failure_callback_url = build_callback_url("/ingestion/staging/dag_failure", callback_params)

    logger.info(
        f"Created IntegrityLink {integrity_link.id} for DAG run {dag_run_id} | "
        f"owner={sec_username} | org={sec_org} | table={staging_table_name}"
    )
    logger.info(f"Success callback URL: {success_callback_url}")
    logger.info(f"Failure callback URL: {failure_callback_url}")
    logger.info(
        f"Triggering staging_dag with source_type: {type.value.upper()} and source: {source}"
    )

    try:
        dag_run_response = get_dag_run_api().trigger_dag_run(
            dag_id="staging_dag",
            trigger_dag_run_post_body=TriggerDAGRunPostBody(
                dag_run_id=dag_run_id,
                conf={
                    "source": str(source),
                    "source_type": type.value.upper(),
                    "staging_table_name": staging_table_name,
                    "success_callback_url": success_callback_url,
                    "failure_callback_url": failure_callback_url,
                },
            ),
        )

        return StagingResponse(
            integrity_link_id=str(integrity_link.id),
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
) -> None:
    """
    Success callback endpoint called by Airflow DAG on successful completion.
    Updates the existing IntegrityLink record with job duration.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)

    Returns:
        Success message with updated IntegrityLink details
    """
    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Ensure created_at exists and is timezone-aware
    if integrity_link.created_at is None:
        raise HTTPException(
            status_code=500,
            detail="IntegrityLink created_at is missing",
        )

    # Calculate job duration
    now = datetime.now(timezone.utc)
    created_at = (
        integrity_link.created_at.replace(tzinfo=timezone.utc)
        if integrity_link.created_at.tzinfo is None
        else integrity_link.created_at
    )
    staging_retrieve_time = now - created_at

    # Update IntegrityLink
    integrity_link.staging_retrieve_time = staging_retrieve_time
    session.commit()
    session.refresh(integrity_link)


@router.post("/dag_failure")
def dag_failure_callback(
    session: SessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
) -> None:
    """
    Failure callback endpoint called by Airflow DAG on failure.
    Deletes the IntegrityLink and drops the staging table.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)

    Returns:
        Success message with cleanup details
    """
    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Get staging table name
    staging_table_name = integrity_link.staging_table_name

    # Drop the staging table if it exists
    try:
        if not staging_table_name:
            raise Exception("Staging table name is missing in IntegrityLink")

        schema = "staging"  # FIXME get it from config
        metadata = MetaData(schema=schema)
        table = Table(staging_table_name, metadata)
        table.drop(session.get_bind(), checkfirst=True)
        session.commit()
    except Exception as e:
        # Log the error but continue with IntegrityLink deletion
        logger.error(f"Error dropping staging table {staging_table_name}: {e}")

    # Delete the IntegrityLink
    session.delete(integrity_link)
    session.commit()
