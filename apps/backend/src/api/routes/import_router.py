import logging
from urllib.parse import urlencode
from uuid import uuid4

from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.dag_run_state import DagRunState
from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from fastapi import APIRouter, Header, HTTPException

from src.api.deps import SessionDep
from src.core.config import get_settings
from src.models import ImportRequest, ImportResponse, StatusResponse
from src.models.data_import import ImportTaskStatus
from src.models.integrity_link import IntegrityLink
from src.services.airflow_client import get_dag_run_api

# Use uvicorn's logger to get colored output
logger = logging.getLogger("uvicorn.error")

router = APIRouter(prefix="/import", tags=["Import"])


def _build_callback_url(route: str, query_params: dict[str, str] | None = None) -> str:
    """Build full callback URL for Airflow DAG callbacks.

    Args:
        route: Backend route path (e.g., '/print_dag_success')
        query_params: Optional query parameters to append to the URL

    Returns:
        Full URL for the callback endpoint with query parameters
    """
    settings = get_settings()
    base_url = f"{settings.datakern_config.get('backend_url', 'default')}{route}"

    if query_params:
        query_string = urlencode(query_params)
        return f"{base_url}?{query_string}"

    return base_url


def dag_run_state_to_import_status(state: DagRunState) -> ImportTaskStatus:
    """Helpers to map DagRunState to ImportTaskStatus"""
    match state:
        case DagRunState.QUEUED:
            return ImportTaskStatus.QUEUED
        case DagRunState.RUNNING:
            return ImportTaskStatus.RUNNING
        case DagRunState.SUCCESS:
            return ImportTaskStatus.SUCCESS
        case DagRunState.FAILED:
            return ImportTaskStatus.FAILED


@router.post(
    "/",
    response_model=ImportResponse,
    summary="Create a new import task",
    description="Submit data for import.",
)
def create_import(
    request: ImportRequest,
    session: SessionDep,
    sec_username: str = Header(..., alias="sec-username"),
    sec_org: str = Header(..., alias="sec-org"),
) -> ImportResponse:
    """
    Create a new import task.

    Args:
        request: Import configuration including type and optional URL
        sec_username: Username from geOrchestra security headers
        sec_org: Organization from geOrchestra security headers

    Returns:
        ImportResponse with DAG ID, DAG run ID, and current status
    """
    dag_run_id = str(uuid4())

    # Generate a fake staging table name for this import
    staging_table_name = f"staging_{dag_run_id.replace('-', '_')[:32]}"

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
    success_callback_url = _build_callback_url("/print_dag_success", callback_params)
    failure_callback_url = _build_callback_url("/print_dag_failure")

    logger.info(
        f"Created IntegrityLink {integrity_link.id} for DAG run {dag_run_id} | "
        f"owner={sec_username} | org={sec_org} | table={staging_table_name}"
    )
    logger.info(f"Success callback URL: {success_callback_url}")

    try:
        dag_run_response = get_dag_run_api().trigger_dag_run(
            dag_id="staging_dag",
            trigger_dag_run_post_body=TriggerDAGRunPostBody(
                dag_run_id=dag_run_id,
                conf={
                    "source": request.url,
                    "source_type": "URL",
                    "success_callback_url": success_callback_url,
                    "failure_callback_url": failure_callback_url,
                },
            ),
        )

        return ImportResponse(
            dag_id=dag_run_response.dag_id,
            dag_run_id=dag_run_response.dag_run_id,
            status=dag_run_state_to_import_status(dag_run_response.state),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.get(
    "/status",
    response_model=StatusResponse,
    summary="Get the status of an import task",
    description="Retrieve the current status of an import task using its task ID.",
)
def get_import_status(dag_id: str, dag_run_id: str) -> StatusResponse:
    """
    Get the status of an import task.

    Args:
        dag_id: The ID of the DAG
        dag_run_id: The ID of the DAG run

    Returns:
        StatusResponse with current status of the import task
    """

    try:
        dag_run = get_dag_run_api().get_dag_run(dag_id, dag_run_id)
        return StatusResponse(
            status=dag_run_state_to_import_status(dag_run.state),
        )
    except NotFoundException:
        return StatusResponse(
            status=ImportTaskStatus.NOT_FOUND,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")
