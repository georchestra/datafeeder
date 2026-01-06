import logging
from pathlib import Path

import geopandas as gpd
from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.engine import Engine

from data_manipulation.logging import configure_logging

logger = logging.getLogger(__name__)
configure_logging(logger)


def _detect_file_encoding(file_path: str) -> str:
    """Detect encoding for geospatial files.

    Args:
        file_path: Path to the file

    Returns:
        Detected encoding string
    """
    path = Path(file_path)

    # Check for .cpg file (encoding file for shapefiles)
    if path.suffix.lower() == ".shp":
        cpg_file = path.with_suffix(".cpg")
        if cpg_file.exists():
            encoding = cpg_file.read_text().strip()
            logger.info(f"Found encoding from .cpg file: {encoding}")
            return encoding

    # For non-shapefile formats (GeoJSON, GeoPackage, etc.), UTF-8 is standard
    # Default to UTF-8 for modern files
    return "utf-8"


def ingest_data_from_file_into_postgis(
    file_path: str,
    table_name: str,
    engine: Engine,
    schema: str | None = None,
) -> None:
    """Ingest data from a file into a PostGIS table."""

    logger.info(f"Ingesting data from file {file_path} into table {table_name}")

    try:
        # Detect encoding (mainly for shapefiles, others default to UTF-8)
        encoding = _detect_file_encoding(file_path)

        # Try reading with detected encoding
        try:
            gdf = gpd.read_file(file_path, encoding=encoding)
        except (UnicodeDecodeError, LookupError):
            # Fallback to common encodings if detection fails
            logger.warning(f"Failed to read with {encoding}, trying latin-1")
            try:
                gdf = gpd.read_file(file_path, encoding="latin-1")
            except (UnicodeDecodeError, LookupError):
                logger.warning("Failed with latin-1, trying cp1252")
                gdf = gpd.read_file(file_path, encoding="cp1252")

        target_schema = schema or "public"

        logger.info(
            f"Ingesting data from file {file_path} into table {table_name} in schema {target_schema}"
        )

        gdf.to_postgis(table_name, engine, if_exists="replace", schema=target_schema)

        # Query the database to get actual row count
        metadata = MetaData(schema=target_schema)
        table = Table(table_name, metadata, autoload_with=engine)
        count_query = select(func.count()).select_from(table)

        with engine.connect() as conn:
            row_count = conn.execute(count_query).scalar()

        logger.info(f"Successfully inserted {row_count} rows into {target_schema}.{table_name}")
    except Exception as e:
        logger.error(f"Error ingesting data from file {file_path}: {e}")
        raise


def ingest_data_from_url_into_postgis(
    url: str, table_name: str, engine: Engine, schema: str | None = None
) -> None:
    """Ingest data from a URL into a PostGIS table."""

    try:
        gdf = gpd.read_file(url)
        target_schema = schema or "public"

        gdf.to_postgis(table_name, engine, if_exists="replace", schema=target_schema)
    except Exception as e:
        logger.error(f"Error ingesting data from URL {url}: {e}")
        raise


def read_data_from_postgis(
    table_name: str, engine: Engine, schema: str | None = None
) -> gpd.GeoDataFrame:
    """Read data from a PostGIS table.

    Args:
        table_name: Name of the table to read
        engine: SQLAlchemy engine
        schema: PostgreSQL schema name (optional)

    Returns:
        GeoDataFrame containing the table data
    """
    try:
        # Use SQLAlchemy Core to safely construct the query
        metadata = MetaData(schema=schema)
        table = Table(table_name, metadata, autoload_with=engine)
        query = select(table)

        # Compile the query to SQL string (with literal binds)
        compiled_query = str(query.compile(engine, compile_kwargs={"literal_binds": True}))

        gdf = gpd.read_postgis(compiled_query, engine)
        return gdf
    except Exception as e:
        table_ref = f"{schema or 'public'}.{table_name}"
        logger.error(f"Error reading data from PostGIS table {table_ref}: {e}")
        raise


def apply_transformations(
    gdf: gpd.GeoDataFrame, transformation_config: dict[str, object]
) -> gpd.GeoDataFrame:
    """Apply transformations to a GeoDataFrame.

    Args:
        gdf: Input GeoDataFrame
        transformation_config: JSON configuration for transformations

    Returns:
        Transformed GeoDataFrame

    Note:
        For now, this function returns the GeoDataFrame without any transformation.
        TODO: Implement transformation logic based on transformation_config.
    """

    return gdf


def write_data_to_postgis(
    gdf: gpd.GeoDataFrame, table_name: str, engine: Engine, schema: str | None = None
) -> None:
    """Write a GeoDataFrame to a final PostGIS table.

    Args:
        gdf: GeoDataFrame to write
        table_name: Name of the target table
        engine: SQLAlchemy engine
        schema: PostgreSQL schema name (optional)
    """
    try:
        target_schema = schema or "public"

        gdf.to_postgis(table_name, engine, if_exists="replace", schema=target_schema)
    except Exception as e:
        table_ref = f"{schema or 'public'}.{table_name}"  # type: ignore
        logger.error(f"Error writing data to PostGIS table {table_ref}: {e}")
        raise
