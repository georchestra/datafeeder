from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from ...models import ImportRequest, ImportResponse, StatusResponse

router = APIRouter(prefix="/v1", tags=["Import"])

# FIXME: in memory store for demo purposes
import_tasks = {}


@router.post(
    "/import",
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
    "/import/status",
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
    task = import_tasks.get(dag_run_id)

    if not task:
        return StatusResponse(
            dag_id=dag_id,
            dag_run_id=dag_run_id,
            status="not_found",
            error="Task not found",
        )

    # Calculate elapsed time since creation
    elapsed_seconds = (datetime.now(timezone.utc) - task["created_at"]).total_seconds()

    # Return "running" if < 3 seconds, "finished" otherwise
    status = "running" if elapsed_seconds < 3 else "finished"

    return StatusResponse(
        dag_id=task["dag_id"],
        dag_run_id=dag_run_id,
        status=status,
        error=None,
    )
