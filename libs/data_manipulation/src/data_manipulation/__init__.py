from data_manipulation.ingestion import (
    ingest_data_from_file_into_postgis,
    ingest_data_from_url_into_postgis,
    read_and_transform_data,
    read_data_from_postgis,
    write_data_to_postgis,
)
from data_manipulation.logging import configure_logging
from data_manipulation.models import (
    CastType,
    ColumnConfig,
    ColumnFilter,
    FilterOperator,
    ForceProjection,
    IntegrityTransformation,
)
from data_manipulation.transformation.filter_sql import build_sql_column_ops
from data_manipulation.transformation.transform import apply_transformations

__all__ = [
    "hello",
    "ingest_data_from_file_into_postgis",
    "ingest_data_from_url_into_postgis",
    "read_data_from_postgis",
    "read_and_transform_data",
    "apply_transformations",
    "build_sql_column_ops",
    "write_data_to_postgis",
    "configure_logging",
    "CastType",
    "ColumnConfig",
    "ColumnFilter",
    "FilterOperator",
    "ForceProjection",
    "IntegrityTransformation",
]


def hello() -> str:
    return "Hello from data_manipulation!"
