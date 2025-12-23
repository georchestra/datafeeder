from pathlib import Path

from fastapi import UploadFile

from src.core.config import get_settings

# curl -v --request POST \
#   --url http://localhost:8080/datakern-backend/import/ \
#   --header 'Content-Type: multipart/form-data' \
#   --form 'type=file' \
#   --form 'file=@my_test_file.json'
async def upload_file_to_temp(file: UploadFile) -> str:
    """Helper to save uploaded file to a temporary location.

    Args:
        file: Uploaded file from the request

    Returns:
        Path to the saved temporary file with scheme (file:// or zip://)
    """
    settings = get_settings()
    tmp_upload_path_str = settings.datakern_config.get("tmp_upload_path", '/tmp/files/')
    
    tmp_upload_path = Path(tmp_upload_path_str.strip('"\' '))
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
        
        scheme = "zip" if file_is_zip else "file"
        source = f"{scheme}://{file_path}"
        
        return source
        
    except Exception as e:
        if file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        raise ValueError(f"Failed to save uploaded file: {str(e)}")