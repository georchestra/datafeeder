from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter

from ...models import ImportRequest, ImportResponse

router = APIRouter(prefix="/api/v1", tags=["Import"])


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
    task_id = str(uuid4())
    return ImportResponse(task_id=task_id, status="pending", created_at=datetime.now(timezone.utc))
