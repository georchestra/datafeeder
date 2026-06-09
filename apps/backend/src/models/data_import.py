from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from data_manipulation.models import CastType as CastType
from data_manipulation.models import ColumnConfig as ColumnConfig
from data_manipulation.models import ColumnFilter as ColumnFilter
from data_manipulation.models import FilterOperator as FilterOperator
from geojson_pydantic import Feature, FeatureCollection
from geojson_pydantic.geometries import Geometry
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.core.task_executor import TaskStatus
from src.models.integrity_link_rule import IntegrityLinkRule
from src.models.recurrence import RecurrencePreset


class ImportType(str, Enum):
    """Supported import types"""

    URL = "url"
    FILE = "file"
    DATABASE = "database"
    API = "api"
    FTP = "ftp"
    EMPTY = "empty"


class FileType(str, Enum):
    """Supported file types"""

    CSV = "csv"
    GEOJSON = "geojson"
    JSON = "json"
    SHAPEFILE = "shapefile"
    GPKG = "gpkg"
    PARQUET = "parquet"
    ZIP = "zip"


EXTENSION_MAP: dict[str, FileType] = {
    "csv": FileType.CSV,
    "geojson": FileType.GEOJSON,
    "json": FileType.JSON,
    "shp": FileType.SHAPEFILE,
    "gpkg": FileType.GPKG,
    "parquet": FileType.PARQUET,
    "geoparquet": FileType.PARQUET,
    "zip": FileType.ZIP,
}


class ProcessRequest(BaseModel):
    """Request model for final import endpoint"""

    integrity_link_id: str
    title: str | None = None
    recurrence: RecurrencePreset | None = None
    generate_metadata_with_ai: bool = False


class UpdateMetadataGnRequest(BaseModel):
    """Payload sent by the frontend to save metadata to GeoNetwork and sync the title."""

    serialized_xml: str
    title: str


class StagingResponse(BaseModel):
    """Response model for import endpoint"""

    integrity_link_id: str
    dag_id: str
    dag_run_id: str
    status: TaskStatus


class ProcessResponse(BaseModel):
    """Response model for final import endpoint"""

    integrity_link_id: str
    dag_id: str
    dag_run_id: str
    status: TaskStatus


class StatusResponse(BaseModel):
    """Response model for status endpoint"""

    status: TaskStatus


class ColumnMetadata(BaseModel):
    """Metadata for a single column (legacy: use ColumnConfig for full configuration)"""

    name: str


class ForceProjection(BaseModel):
    """Force projection configuration for coordinate columns"""

    type: str = ""  # e.g., "EPSG:4326"
    y_column: str | None = None
    x_column: str | None = None


class StagingMetadata(BaseModel):
    """Metadata for staging data"""

    columns: list[ColumnConfig]
    title: str
    file_type: FileType | None
    force_projection: ForceProjection | None = None
    original_projection: str | None = None


class StagingMetadataResponse(StagingMetadata):
    """Metadata for staging data"""

    import_type: ImportType
    row_count: int
    has_final_table: bool
    layer_name: str | None = None


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
    source_layer: str | None = None
    source_protocol: str | None = None
    staging_table_name: str | None
    final_table_name: str | None
    metadata_id: str | None
    data_id: str | None
    created_at: datetime | None
    last_retrieval_timestamp: datetime | None
    schedule: str | None
    schedule_enabled: bool
    preset_id: RecurrencePreset | None = None
    access_level: str | None = Field(
        default=None,
        description="User's effective access level: ADMIN, OWNER, WRITE, or READ",
    )
    gn_is_published: bool = False
    gs_is_published: bool = False
    has_integrity_rules: bool = False
    has_final_table: bool = False
    owner_display_name: str | None = None

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid_to_str(cls, v: UUID | str | None) -> str:
        """Convert UUID to string for serialization."""
        return str(v) if v is not None else ""


class IntegrityLinkListResponse(BaseModel):
    """Response for integrity links list with lazy loading support."""

    items: list[IntegrityLinkListItem]
    has_more: bool
    offset: int
    next_offset: int  # raw DB offset to pass verbatim on the next page request


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
    source_layer: str | None = None
    source_protocol: str | None = None
    source_file_name: str | None
    source_file_type: FileType | None
    source_username: str | None
    staging_table_name: str | None
    staging_retrieve_time: timedelta | None
    final_table_name: str | None
    last_retrieval_timestamp: datetime | None
    schedule: str | None
    schedule_enabled: bool
    preset_id: RecurrencePreset | None = None
    created_at: datetime | None
    gn_is_published: bool | None
    gs_is_published: bool | None
    access_level: str | None = None


class IntegrityLinkGsPublishResponse(IntegrityLinkResponse):
    """IntegrityLinkResponse augmented with GeoServer ACL read roles after a publish/unpublish operation."""

    gs_read_roles: list[str] | None = None
    rules: list[IntegrityLinkRule] = []
