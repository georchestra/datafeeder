from data_manipulation.ingestion import (
    ingest_data_from_file_into_postgis,
    ingest_data_from_ogc_service_into_postgis,
    ingest_data_from_url_into_postgis,
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
from data_manipulation.postgis_writer import write_arrow_to_postgis
from data_manipulation.transformation.filter_sql import build_filter_clause
from data_manipulation.transformation.transform_sql import (
    PreviewResult,
    TransformationQuery,
    detect_table_srid,
    read_transformed_preview,
    transform_staging_to_final,
)
from data_manipulation.type_detection import detect_column_type_from_sqla

__all__ = [
    "hello",
    "ingest_data_from_file_into_postgis",
    "ingest_data_from_ogc_service_into_postgis",
    "ingest_data_from_url_into_postgis",
    "write_arrow_to_postgis",
    "build_filter_clause",
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
