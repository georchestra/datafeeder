from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from airflow_client.client.models.dag_run_state import DagRunState
from geojson_pydantic import Feature, FeatureCollection
from geojson_pydantic.geometries import Geometry
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ImportType(str, Enum):
    """Supported import types"""

    URL = "url"
    FILE = "file"
    DATABASE = "database"
    API = "api"
    FTP = "ftp"


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


class ForceProjection(BaseModel):
    """Force projection configuration for coordinate columns"""

    type: str = ""  # e.g., "EPSG:4326"
    y_column: str | None = None
    x_column: str | None = None


class StagingMetadata(BaseModel):
    """Metadata for staging data"""

    columns: list[ColumnMetadata]
    title: str
    file_type: FileType | None
    force_projection: ForceProjection | None = None
    original_projection: str | None = None


class StagingMetadataResponse(StagingMetadata):
    """Metadata for staging data"""

    import_type: ImportType
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


class IntegrityLinkListItem(BaseModel):
    """Response model for integrity link in list view (excludes sensitive fields)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    integrity_title: str | None
    integrity_owner: str
    integrity_organization: str
    source_import_type: ImportType
    source_file_name: str | None
    source_file_type: FileType | None
    source_url: str | None
    staging_table_name: str
    final_table_name: str | None
    metadata_id: str | None
    data_id: str | None
    created_at: datetime | None
    last_retrieval_timestamp: datetime | None
    schedule: str | None
    schedule_enabled: bool

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: UUID | str | None) -> str:
        """Convert UUID to string for serialization."""
        return str(v) if v is not None else ""


class IntegrityLinkListResponse(BaseModel):
    """Response for integrity links list with lazy loading support."""

    items: list[IntegrityLinkListItem]
    has_more: bool  # True if there are more items to load
    offset: int  # Current offset (for next request: offset + BATCH_SIZE)


class IntegrityLinkResponse(BaseModel):
    """Response model for IntegrityLink entity."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    data_id: str | None
    metadata_id: str | None
    integrity_title: str | None
    integrity_owner: str
    integrity_organization: str
    integrity_transformation: dict[str, Any] | None = None
    source_import_type: ImportType
    source_url: str | None
    source_file_name: str | None
    source_file_type: FileType | None
    source_username: str | None
    staging_table_name: str
    staging_retrieve_time: timedelta | None
    final_table_name: str | None
    last_retrieval_timestamp: datetime | None
    schedule: str | None
    schedule_enabled: bool
    created_at: datetime | None
