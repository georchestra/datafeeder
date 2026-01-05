from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.core.config import get_settings

router = APIRouter(prefix="/files", tags=["Files"])

DEFAULT_FILES_FOLDER = Path("/tmp/files")


def read_file(filename: str) -> FileResponse:
    """
    Read a file from the default files folder.

    Args:
        filename: The name of the file to read

    Returns:
        FileResponse with the file content

    Raises:
        HTTPException: If file not found or access error
    """
    settings = get_settings()
    file_path = Path(settings.TMP_UPLOAD_PATH) / filename
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found")

    return FileResponse(path=file_path, filename=filename)


@router.get(
    "/{filename}",
    summary="Read a file from the default folder",
    description="Retrieve the content of a file from /tmp/files folder.",
)
def get_file(filename: str) -> FileResponse:
    """
    Get a file from the default files folder.

    Args:
        filename: The name of the file to read

    Returns:
        FileResponse with the file content
    """

    # TODO: add security checks only allow airflow to read the file!!!!

    return read_file(filename)
