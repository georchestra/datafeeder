"""Data transformation models."""

from pydantic import BaseModel, Field


class ForceProjection(BaseModel):
    """Force projection configuration (from coordinates)."""

    type: str = Field(default="", description="Projection type, e.g., 'EPSG:4326'")
    y_column: str | None = Field(default=None, description="Latitude/Y coordinate column name")
    x_column: str | None = Field(default=None, description="Longitude/X coordinate column name")


class ColumnConfig(BaseModel):
    """Column configuration for transformation."""

    name: str = Field(..., description="Column name")


class IntegrityTransformation(BaseModel):
    """Configuration for data transformation during processing."""

    columns: list[ColumnConfig] | None = Field(
        default=None, description="List of column configurations to include in transformation"
    )
    force_projection: ForceProjection | None = Field(
        default=None, description="Projection configuration for coordinate transformation"
    )
