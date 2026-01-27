from enum import Enum
from typing import Any

from airflow_client.client.models.dag_run_state import DagRunState
from geojson_pydantic import Feature, FeatureCollection
from geojson_pydantic.geometries import Geometry
from pydantic import BaseModel, Field


class ImportType(str, Enum):
    """Supported import types"""

    URL = "url"
    FILE = "file"
    DATABASE = "database"
    API = "api"


class FileType(str, Enum):
    """Supported file types"""

    CSV = "csv"
    GEOJSON = "geojson"
    JSON = "json"
    SHAPEFILE = "shapefile"
    GPKG = "gpkg"
    ZIP = "zip"


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


class ColumnMetadata(BaseModel):
    """Metadata for a single column"""

    name: str


class StagingMetadataResponse(BaseModel):
    """Metadata for staging data"""

    title: str
    import_type: ImportType
    file_type: FileType | None

    columns: list[ColumnMetadata]
    row_count: int


class StagingPreviewResponse(BaseModel):
    """Preview data from staging table"""

    data: list[dict[str, Any]]
    geojson: FeatureCollection[Feature[Geometry, dict[str, Any]]] | None = Field(
        default=None,
        description="GeoJSON FeatureCollection, only present for geographic data",
    )
    is_geographic: bool = Field(
        default=False,
        description="Indicates if the staging table contains geometry data",
    )
