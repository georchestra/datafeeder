from data_manipulation.ingestion import (
    ingest_data_from_database_into_postgis,
    ingest_data_from_file_into_postgis,
    ingest_data_from_ftp_into_postgis,
    ingest_data_from_ogc_service_into_postgis,
    ingest_data_from_url_into_postgis,
    ingest_file_with_ogr2ogr,
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
from data_manipulation.transformation.filter_sql import build_filter_clause, build_sql_column_ops
from data_manipulation.transformation.sql_transform import (
    PreviewResult,
    TransformationQuery,
    build_transformation_select,
    detect_table_srid,
    read_transformed_preview,
    transform_staging_to_final,
)
from data_manipulation.type_detection import detect_column_type_from_sqla

__all__ = [
    "hello",
    "ingest_data_from_database_into_postgis",
    "ingest_data_from_file_into_postgis",
    "ingest_data_from_ftp_into_postgis",
    "ingest_data_from_ogc_service_into_postgis",
    "ingest_data_from_url_into_postgis",
    "ingest_file_with_ogr2ogr",
    "build_sql_column_ops",
    "build_filter_clause",
    "build_transformation_select",
    "transform_staging_to_final",
    "read_transformed_preview",
    "detect_table_srid",
    "PreviewResult",
    "TransformationQuery",
    "detect_column_type_from_sqla",
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
