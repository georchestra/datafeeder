from enum import Enum

from pydantic import AnyUrl, BaseModel
from airflow_client.client.models.dag_run_state import DagRunState


class ImportType(str, Enum):
    """Supported import types"""

    URL = "url"
    FILE = "file"
    DATABASE = "database"
    API = "api"


class StagingRequest(BaseModel):
    """Request model for import endpoint"""

    type: ImportType
    url: AnyUrl


class TransformationConfig(BaseModel):
    """Transformation configuration model"""

    crs: str | None
    # TODO: add more fields as needed


class ProcessRequest(BaseModel):
    """Request model for final import endpoint"""

    title: str
    # config: TransformationConfig
    # cron_schedule: str | None

    # TODO: Replace by integrity_link_id
    staging_table_name: str


class StagingResponse(BaseModel):
    """Response model for import endpoint"""

    dag_id: str
    dag_run_id: str
    status: DagRunState

    # TODO: Replace by integrity_link_id
    staging_table_name: str


class ProcessResponse(BaseModel):
    """Response model for final import endpoint"""

    dag_id: str
    dag_run_id: str
    status: DagRunState


class StatusResponse(BaseModel):
    """Response model for status endpoint"""

    status: DagRunState
