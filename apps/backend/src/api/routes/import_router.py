from uuid import uuid4

from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.dag_run_state import DagRunState
from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from fastapi import APIRouter, HTTPException

from src.models import ImportRequest, ImportResponse, StatusResponse
from src.models.data_import import ImportTaskStatus
from src.services.airflow_client import get_dag_run_api

router = APIRouter(prefix="/import", tags=["Import"])


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
def create_import(request: ImportRequest) -> ImportResponse:
    """
    Create a new import task.

    Args:
        request: Import configuration including type and optional URL

    Returns:
        ImportResponse with DAG ID, DAG run ID, and current status
    """
    dag_run_id = str(uuid4())
    dag_run_response = get_dag_run_api().trigger_dag_run(
        dag_id="my_first_dag",
        trigger_dag_run_post_body=TriggerDAGRunPostBody(
            dag_run_id=dag_run_id,
        ),
    )

    return ImportResponse(
        dag_id=dag_run_response.dag_id,
        dag_run_id=dag_run_response.dag_run_id,
        status=dag_run_state_to_import_status(dag_run_response.state),
    )


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
