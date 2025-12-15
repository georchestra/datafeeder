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


class FinalImportRequest(BaseModel):
    """Request model for final import endpoint"""

    staging_table_name: str
    final_table_name: str


class ImportResponse(BaseModel):
    """Response model for import endpoint"""

    dag_id: str
    dag_run_id: str
    status: ImportTaskStatus


class StatusResponse(BaseModel):
    """Response model for status endpoint"""

    status: ImportTaskStatus
