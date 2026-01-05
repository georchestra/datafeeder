from pathlib import Path

from fastapi import UploadFile

from src.core.config import get_settings


async def upload_file_to_temp(file: UploadFile) -> str:
    """Helper to save uploaded file to a temporary location.

    Usage
    ----------
     curl -v --request POST \
        --url http://localhost:8080/datakern-backend/ingestion/staging/ \
        --header 'Content-Type: multipart/form-data' \
        --form 'type=file' \
        --form 'file=@my_test_file.json'

    Args:
        file: Uploaded file from the request

    Returns:
        The unique file name in the temporary upload directory
    """
    settings = get_settings()

    tmp_upload_path = Path(settings.TMP_UPLOAD_PATH)
    tmp_upload_path.mkdir(parents=True, exist_ok=True)

    original_filename = file.filename or "uploaded_file"
    original_path = Path(original_filename)

    import uuid

    unique_id = uuid.uuid4().hex[:8]
    extension = original_path.suffix
    unique_filename = f"{original_path.stem}_{unique_id}{extension}"

    file_path = tmp_upload_path / unique_filename

    file_is_zip = False
    if extension:
        file_is_zip = extension.lower() == ".zip"
    if file.content_type:
        file_is_zip = file_is_zip or file.content_type == "application/zip"

        # TODO: vérifier zip, semble ne pas marcher
        # TODO: vérifier shp file

    try:
        content = await file.read()
        if not content:
            raise ValueError("Empty file uploaded")

        file_path.write_bytes(content)

        if not file_path.exists():
            raise IOError(f"File was not created: {file_path}")

        return unique_filename

    except Exception as e:
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass
        raise ValueError(f"Failed to save uploaded file: {str(e)}")


def get_temp_file_url(filename: str) -> str:
    """Get the backend url to a temporary uploaded file, eg. "http://localhost:8000/files/the_given_filename"

    Args:
        filename: The unique file name in the temporary upload directory

    Returns:
        Full url to the temporary uploaded file
    """
    settings = get_settings()
    file_url = settings.BACKEND_URL + "/files/" + filename

    return file_url
