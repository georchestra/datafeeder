# from typing import Optional
# from uuid import uuid4
# from pathlib import Path

# from airflow_client.client.exceptions import NotFoundException
# from airflow_client.client.models.dag_run_state import DagRunState
# from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
# from fastapi import APIRouter, Form, HTTPException, File, UploadFile

# from src.core.config import get_settings
# from src.models import ImportResponse, StatusResponse
# from src.models.data_import import ImportTaskStatus, ImportType
# from src.services.airflow_client import get_dag_run_api

# router = APIRouter(prefix="/import", tags=["Import"])


# def _build_callback_url(route: str) -> str:
#     """Build full callback URL for Airflow DAG callbacks.

#     Args:
#         route: Backend route path (e.g., '/print_dag_success')

#     Returns:
#         Full URL for the callback endpoint
#     """
#     settings = get_settings()
#     return f"{settings.datakern_config.get('backend_url', 'default')}{route}"


# def dag_run_state_to_import_status(state: DagRunState) -> ImportTaskStatus:
#     """Helpers to map DagRunState to ImportTaskStatus"""
#     match state:
#         case DagRunState.QUEUED:
#             return ImportTaskStatus.QUEUED
#         case DagRunState.RUNNING:
#             return ImportTaskStatus.RUNNING
#         case DagRunState.SUCCESS:
#             return ImportTaskStatus.SUCCESS
#         case DagRunState.FAILED:
#             return ImportTaskStatus.FAILED


# # curl -v --request POST \
# #   --url http://localhost:8080/datakern-backend/import/ \
# #   --header 'Content-Type: multipart/form-data' \
# #   --form 'type=file' \
# #   --form 'file=@my_test_file.json'
# async def upload_file_to_temp(file: UploadFile) -> str:
#     """Helper to save uploaded file to a temporary location.

#     Args:
#         file: Uploaded file from the request

#     Returns:
#         Path to the saved temporary file with scheme (file:// or zip://)
#     """
#     settings = get_settings()
#     tmp_upload_path_str = settings.datakern_config.get("tmp_upload_path", '/tmp/files/')
    
#     tmp_upload_path = Path(tmp_upload_path_str.strip('"\' '))
#     tmp_upload_path.mkdir(parents=True, exist_ok=True)
    
#     original_filename = file.filename or "uploaded_file"
#     original_path = Path(original_filename)
    
#     import uuid
#     unique_id = uuid.uuid4().hex[:8]
#     extension = original_path.suffix
#     unique_filename = f"{original_path.stem}_{unique_id}{extension}"
    
#     file_path = tmp_upload_path / unique_filename
    
#     file_is_zip = False
#     if extension:
#         file_is_zip = extension.lower() == ".zip"
#     if file.content_type:
#         file_is_zip = file_is_zip or file.content_type == "application/zip"
        
#     try:
#         content = await file.read()
#         if not content:
#             raise ValueError("Empty file uploaded")
        
#         file_path.write_bytes(content)
        
#         if not file_path.exists():
#             raise IOError(f"File was not created: {file_path}")
        
#         scheme = "zip" if file_is_zip else "file"
#         source = f"{scheme}://{file_path}"
        
#         return source
        
#     except Exception as e:
#         if file_path.exists():
#             try:
#                 file_path.unlink()
#             except:
#                 pass
#         raise ValueError(f"Failed to save uploaded file: {str(e)}")


# @router.post(
#     "/",
#     response_model=ImportResponse,
#     summary="Create a new import task",
#     description="Submit data for import.",
# )
# async def create_import(
#     type: ImportType = Form(...),
#     url: Optional[str] = Form(None),
#     file: Optional[UploadFile] = File(None)
# ) -> ImportResponse:
#     """
#     Create a new import task.

#     Args:
#         request: Import configuration including type and optional URL

#     Returns:
#         ImportResponse with DAG ID, DAG run ID, and current status
#     """
#     dag_run_id = str(uuid4())

#     print(_build_callback_url("/print_dag_success"))

#     if type == ImportType.FILE:
#         if file is None:
#             raise HTTPException(status_code=400, detail="File is required")
        
#         source = await upload_file_to_temp(file)

#     else:
#         source = url

#     try:
#         dag_run_response = get_dag_run_api().trigger_dag_run(
#             dag_id="staging_dag",
#             trigger_dag_run_post_body=TriggerDAGRunPostBody(
#                 dag_run_id=dag_run_id,
#                 conf={
#                     "source": source,
#                     "source_type": "URL",
#                     "success_callback_url": _build_callback_url("/print_dag_success"),
#                     "failure_callback_url": _build_callback_url("/print_dag_failure"),
#                 },
#             ),
#         )

#         return ImportResponse(
#             dag_id=dag_run_response.dag_id,
#             dag_run_id=dag_run_response.dag_run_id,
#             status=dag_run_state_to_import_status(dag_run_response.state),
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


# @router.get(
#     "/status",
#     response_model=StatusResponse,
#     summary="Get the status of an import task",
#     description="Retrieve the current status of an import task using its task ID.",
# )
# def get_import_status(dag_id: str, dag_run_id: str) -> StatusResponse:
#     """
#     Get the status of an import task.

#     Args:
#         dag_id: The ID of the DAG
#         dag_run_id: The ID of the DAG run

#     Returns:
#         StatusResponse with current status of the import task
#     """

#     try:
#         dag_run = get_dag_run_api().get_dag_run(dag_id, dag_run_id)
#         return StatusResponse(
#             status=dag_run_state_to_import_status(dag_run.state),
#         )
#     except NotFoundException:
#         return StatusResponse(
#             status=ImportTaskStatus.NOT_FOUND,
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Airflow error: {e}")
