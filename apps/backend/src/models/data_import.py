from enum import Enum

from airflow_client.client.models.dag_run_state import DagRunState
from fastapi import File, Form, UploadFile
from pydantic import AnyUrl, BaseModel


class ImportType(str, Enum):
    """Supported import types"""

    URL = "url"
    FILE = "file"
    DATABASE = "database"
    API = "api"


class StagingRequest(BaseModel):
    """Request model for import endpoint"""

    type: ImportType = Form(...)
    url: AnyUrl | None = Form(None)
    file: UploadFile | None = File(None)


class TransformationConfig(BaseModel):
    """Transformation configuration model"""

    crs: str | None
    # TODO: add more fields as needed


class ProcessRequest(BaseModel):
    """Request model for final import endpoint"""

    integrity_link_id: str
    title: str
    # config: TransformationConfig
    # cron_schedule: str | None


class StagingResponse(BaseModel):
    """Response model for import endpoint"""

    integrity_link_id: str
    dag_id: str
    dag_run_id: str
    status: DagRunState


class ProcessResponse(BaseModel):
    """Response model for final import endpoint"""

    integrity_link_id: str
    dag_id: str
    dag_run_id: str
    status: DagRunState


class StatusResponse(BaseModel):
    """Response model for status endpoint"""

    status: DagRunState
