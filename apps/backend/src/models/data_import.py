from enum import Enum

from pydantic import AnyUrl, BaseModel


class ImportType(str, Enum):
    """Supported import types"""

    URL = "url"
    FILE = "file"
    DATABASE = "database"
    API = "api"


class ImportTaskStatus(str, Enum):
    """Possible task statuses"""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    NOT_FOUND = "not_found"


class StagingImportRequest(BaseModel):
    """Request model for import endpoint"""

    type: ImportType
    url: AnyUrl


class TransformationConfig(BaseModel):
    """Transformation configuration model"""

    crs: str | None
    # TODO: add more fields as needed


class FinalImportRequest(BaseModel):
    """Request model for final import endpoint"""

    title: str
    # config: TransformationConfig
    # cron_schedule: str | None

    # TODO: Replace by integrity_link_id
    staging_table_name: str


class StagingImportResponse(BaseModel):
    """Response model for import endpoint"""

    dag_id: str
    dag_run_id: str
    status: ImportTaskStatus

    # TODO: Replace by integrity_link_id
    staging_table_name: str


class FinalImportResponse(BaseModel):
    """Response model for final import endpoint"""

    dag_id: str
    dag_run_id: str
    status: ImportTaskStatus


class StatusResponse(BaseModel):
    """Response model for status endpoint"""

    status: ImportTaskStatus
