from datetime import datetime, timezone
from uuid import uuid4

from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.dag_run_state import DagRunState
from fastapi import APIRouter, HTTPException

from src.models import ImportRequest, ImportResponse, StatusResponse
from src.models.data_import import ImportTaskStatus
from src.services.airflow_client import get_dag_run_api

router = APIRouter(prefix="/import", tags=["Import"])


@router.post(
    "/",
    response_model=ImportResponse,
    summary="Create a new import task",
    description="Submit data for import. Returns a task ID for tracking the async import process.",
)
def create_import(request: ImportRequest) -> ImportResponse:
    """
    Create a new import task.

    Args:
        request: Import configuration including type and optional URL

    Returns:
        ImportResponse with task_id, status, and timestamp
    """
    dag_id = str(uuid4())
    dag_run_id = str(uuid4())
    import_tasks[dag_run_id] = {
        "dag_id": dag_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    }
    return ImportResponse(dag_id=dag_id, dag_run_id=dag_run_id, status="pending")


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
        StatusResponse with current status and timestamps
    """

    try:
        dag_run = get_dag_run_api().get_dag_run(dag_id, dag_run_id)
        
        match dag_run.state:
            case DagRunState.QUEUED:
                status = ImportTaskStatus.QUEUED
            case DagRunState.RUNNING:
                status = ImportTaskStatus.RUNNING
            case DagRunState.SUCCESS:
                status = ImportTaskStatus.SUCCESS
            case DagRunState.FAILED:
                status = ImportTaskStatus.FAILED

        return StatusResponse(
            status=status,
        )
    except NotFoundException:
        return StatusResponse(
            status=ImportTaskStatus.NOT_FOUND,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")
