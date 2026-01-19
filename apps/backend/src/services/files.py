import uuid
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from src.core.config import get_settings
from src.models.data_import import FileType


async def upload_file_to_temp(
    file: UploadFile, rand_id: Optional[str] = None
) -> tuple[str, FileType, str]:
    """Helper to save uploaded file to a temporary location.

    Args:
        file: Uploaded file from the request
        rand_id: Optional random ID to use for the file name, you can give the dag id for instance

    Returns:
        A tuple containing (source_file_name, source_file_type, file_url)
    """
    settings = get_settings()

    tmp_upload_path = Path(settings.TMP_UPLOAD_PATH)
    tmp_upload_path.mkdir(parents=True, exist_ok=True)

    original_filename = file.filename or "uploaded_file"
    original_path = Path(original_filename)

    unique_id = rand_id or uuid.uuid4().hex[:8]
    extension = original_path.suffix
    unique_filename = f"{original_path.stem}_{unique_id}{extension}"

    file_path = tmp_upload_path / unique_filename

    file_is_zip = False
    if extension:
        file_is_zip = extension.lower() == ".zip"
    if file.content_type:
        file_is_zip = file_is_zip or file.content_type == "application/zip"

    try:
        content = await file.read()
        if not content:
            raise ValueError("Empty file uploaded")

        file_path.write_bytes(content)

        if not file_path.exists():
            raise IOError(f"File was not created: {file_path}")

        file_url = get_temp_file_url(unique_filename)
        source_file_name = unique_filename
        source_file_type = FileType(extension.lstrip(".").lower())

        return source_file_name, source_file_type, file_url

    except Exception as e:
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        raise ValueError(f"Failed to save uploaded file: {str(e)}")


def get_temp_file_dir_path() -> str:
    """Get the temporary upload directory path.

    Returns:
        The temporary upload directory path
    """
    settings = get_settings()
    temp_file_folder = settings.BACKEND_URL + "/internal/files/"

    return temp_file_folder


def get_temp_file_url(filename: str) -> str:
    """Get the backend url to a temporary uploaded file, eg. "http://localhost:8000/internal/files/the_given_filename"

    Args:
        filename: The unique file name in the temporary upload directory

    Returns:
        Full url to the temporary uploaded file
    """
    file_url = get_temp_file_dir_path() + filename

    return file_url


def delete_temp_file(file_url: str) -> None:
    """Delete a temporary file from the upload directory.

    Args:
        file_url: The file URL to delete

    Returns:
        True if file was deleted, False if file didn't exist

    Raises:
        Exception: If deletion fails for reasons other than file not existing
    """
    settings = get_settings()

    if file_url.startswith(get_temp_file_dir_path()):
        filename = file_url.rsplit("/", 1)[-1]  # Extract the filename from the URL
        file_path = Path(settings.TMP_UPLOAD_PATH) / filename

        if not file_path.exists():
            raise IOError(f"Unable to delete: {filename}")

        file_path.unlink()
