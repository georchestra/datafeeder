"""Data transformation models."""

from enum import StrEnum

from pydantic import BaseModel, Field


class FilterOperator(StrEnum):
    """Filter comparison operator for column filtering."""

    EXACTLY = "exactly"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"


class CastType(StrEnum):
    """Target data type for column casting."""

    BOOLEAN = "boolean"
    NUMERIC = "numeric"
    TEXT = "text"
    DATE = "date"


class ForceProjection(BaseModel):
    """Force projection configuration (from coordinates)."""

    type: str = Field(default="", description="Projection type, e.g., 'EPSG:4326'")
    y_column: str | None = Field(default=None, description="Latitude/Y coordinate column name")
    x_column: str | None = Field(default=None, description="Longitude/X coordinate column name")


class ColumnFilter(BaseModel):
    """Filter applied to a single column."""

    operator: FilterOperator = Field(..., description="Filter comparison operator")
    value: str = Field(..., min_length=1, description="Filter value to match against")


class ColumnConfig(BaseModel):
    """Column configuration for transformation."""

    original_name: str = Field(
        ..., description="Original column name from staging table (immutable reference)"
    )
    original_type: CastType = Field(
        default=CastType.TEXT,
        description=(
            "Detected source column type. TEXT used as fallback for geometry and unknown types."
        ),
    )
    new_name: str | None = Field(
        default=None, description="Renamed column name. None = keep original name."
    )
    excluded: bool = Field(default=False, description="Whether the column is excluded from output")
    cast_type: CastType | None = Field(
        default=None,
        description="Target data type for casting. None = keep original type.",
    )
    filter: ColumnFilter | None = Field(
        default=None, description="Active filter on this column. None = no filter."
    )


class JoinConfig(BaseModel):
    """LEFT JOIN of the staging table with another table of the same (data) database."""

    table_schema: str = Field(..., description="Schema of the table to join, e.g. an org schema")
    table_name: str = Field(..., description="Name of the table to join")
    source_column: str = Field(..., description="Join key column of the staging table")
    target_column: str = Field(..., description="Join key column of the joined table")
    columns: list[str] = Field(
        default_factory=list,
        description="Columns of the joined table to add to the output. Empty = no join.",
    )


class IntegrityTransformation(BaseModel):
    """Configuration for data transformation during processing."""

    columns: list[ColumnConfig] | None = Field(
        default=None, description="List of column configurations to include in transformation"
    )
    force_projection: ForceProjection | None = Field(
        default=None, description="Projection configuration for coordinate transformation"
    )
    join: JoinConfig | None = Field(
        default=None, description="Optional join with another table of the data database"
    )
