from enum import Enum

from pydantic import BaseModel


class ImportType(str, Enum):
    """Supported import types"""

    URL = "url"
    FILE = "file"
    DATABASE = "database"
    API = "api"


class ImportRequest(BaseModel):
    """Request model for import endpoint"""

    type: ImportType
    url: str | None = None


class ImportResponse(BaseModel):
    """Response model for import endpoint"""

    dag_id: str
    dag_run_id: str
    status: str


class StatusResponse(BaseModel):
    """Response model for status endpoint"""

    dag_id: str
    dag_run_id: str
    status: str
    error: str | None = None
