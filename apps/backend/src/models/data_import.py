from datetime import datetime
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

    task_id: str
    status: str
    created_at: datetime
