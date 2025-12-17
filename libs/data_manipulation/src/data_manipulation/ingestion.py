import logging

import geopandas as gpd
from sqlalchemy import MetaData, Table, select
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ingest_data_from_file_into_postgis(
    file_path: str, table_name: str, engine: Engine, schema: str | None = None
) -> None:
    """Ingest data from a file into a PostGIS table."""

    try:
        gdf = gpd.read_file(file_path)
        target_schema = schema or "public"

        gdf.to_postgis(table_name, engine, if_exists="replace", schema=target_schema)
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

        gdf = gpd.read_postgis(query, engine, geom_col="geometry")
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
