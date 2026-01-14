import logging
import tempfile
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.engine import Engine

from data_manipulation.logging import configure_logging
from data_manipulation.validators import validate_table_name

logger = logging.getLogger(__name__)
configure_logging(logger)

DEFAULT_SCHEMA = "public"
DEFAULT_GEOMETRY_COLUMN = "geom"

def _get_table_row_count(table_name: str, engine: Engine, schema: str) -> int:
    metadata = MetaData(schema=schema)
    table = Table(table_name, metadata, autoload_with=engine)
    count_query = select(func.count()).select_from(table)

    with engine.connect() as conn:
        return conn.execute(count_query).scalar() or 0


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
    schema: str = DEFAULT_SCHEMA,
) -> None:
    """Ingest data from a file into a PostGIS table.

    Args:
        file_path: Path to the input file
        table_name: Target table name in PostGIS
        engine: SQLAlchemy engine
        schema: Target schema (default: public)
    """
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

        write_data_to_postgis(gdf, table_name, engine, schema)
    except Exception as e:
        logger.error(f"Error ingesting data from file {file_path}: {e}")
        raise


def ingest_data_from_url_into_postgis(
    url: str,
    table_name: str,
    engine: Engine,
    schema: str = DEFAULT_SCHEMA,
    auth: tuple[str, str] | None = None,
) -> None:
    """Ingest data from a URL into a PostGIS table.

    Args:
        url: URL to download data from
        table_name: Target table name in PostGIS
        engine: SQLAlchemy engine
        schema: Target schema (default: public)
        auth: Optional tuple of (username, password) for HTTP Basic Authentication
    """
    try:
        if auth:
            # Download file first (GeoPandas doesn't support Basic Auth natively)
            logger.info(f"Downloading file from {url} with Basic Authentication")

            response = requests.get(url, auth=auth, timeout=300)
            response.raise_for_status()

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_path = Path(temp_dir) / Path(url).name
                with open(temp_file_path, "wb") as temp_file:
                    temp_file.write(response.content)

                gdf = gpd.read_file(temp_file_path)
        else:
            gdf = gpd.read_file(url)

        logger.info(
            f"Ingesting data from URL {url} into table {table_name} in schema {schema}"
        )

        write_data_to_postgis(gdf, table_name, engine, schema)
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
    # Validate table name to prevent SQL injection
    validate_table_name(table_name)

    try:
        # Use SQLAlchemy Core to safely construct the query
        metadata = MetaData(schema=schema)
        table = Table(table_name, metadata, autoload_with=engine)
        query = select(table)

        # Compile the query to SQL string (with literal binds)
        compiled_query = str(query.compile(engine, compile_kwargs={"literal_binds": True}))

        gdf = gpd.read_postgis(compiled_query, engine, geom_col=DEFAULT_GEOMETRY_COLUMN)
        return gdf
    except Exception as e:
        logger.error(f"Error reading data from PostGIS table {schema}.{table_name}: {e}")
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
    gdf: gpd.GeoDataFrame | pd.DataFrame, table_name: str, engine: Engine, schema: str = DEFAULT_SCHEMA
) -> None:
    """Write a GeoDataFrame or DataFrame to a PostGIS table.

    Args:
        gdf: GeoDataFrame or DataFrame to write
        table_name: Name of the target table
        engine: SQLAlchemy engine
        schema: PostgreSQL schema name (optional)
    """
    # Validate table name to prevent SQL injection
    validate_table_name(table_name)

    try:
        if not isinstance(gdf, gpd.GeoDataFrame): # DataFrame
            # Ensure there is no geom column
            if DEFAULT_GEOMETRY_COLUMN in gdf.columns:
                logger.warning(
                    f"DataFrame already has a '{DEFAULT_GEOMETRY_COLUMN}' column. Dropping it before writing to PostGIS."
                )
                gdf = gdf.drop(columns=[DEFAULT_GEOMETRY_COLUMN])

            # Write data to PostGIS as a regular table
            gdf.to_sql(table_name, engine, if_exists="replace", schema=schema, index=False)
        else: # GeoDataFrame
            # Ensure the geometry column is named 'geom' for PostGIS convention
            if gdf.active_geometry_name is None:
                logger.info("GeoDataFrame has no active geometry column set.")
                
                # Ensure there is no geom column
                if DEFAULT_GEOMETRY_COLUMN in gdf.columns:
                    logger.warning(
                        f"GeoDataFrame already has a '{DEFAULT_GEOMETRY_COLUMN}' column."
                        " Dropping it before writing to PostGIS."
                    )
                    gdf = gdf.drop(columns=[DEFAULT_GEOMETRY_COLUMN])

            elif gdf.active_geometry_name is DEFAULT_GEOMETRY_COLUMN:
                logger.info(f"GeoDataFrame has '{DEFAULT_GEOMETRY_COLUMN}' as active geometry column.")
            else:
                logger.info(f"GeoDataFrame has '{gdf.active_geometry_name}' as active geometry column.")

                if DEFAULT_GEOMETRY_COLUMN in gdf.columns:
                    logger.warning(
                        f"GeoDataFrame already has a '{DEFAULT_GEOMETRY_COLUMN}' column."
                        " Overwriting it with the active geometry column."
                    )

                logger.info(f"Renaming active geometry column to '{DEFAULT_GEOMETRY_COLUMN}'")
                gdf.rename_geometry(DEFAULT_GEOMETRY_COLUMN, inplace=True)
            
            # Write data to PostGIS
            gdf.to_postgis(table_name, engine, if_exists="replace", schema=schema, index=False)

        # Log the number of inserted rows
        row_count = _get_table_row_count(table_name, engine, schema)
        logger.info(f"Successfully inserted {row_count} rows into {schema}.{table_name}")
    except Exception as e:
        logger.error(f"Error writing data to PostGIS table {schema}.{table_name}: {e}")
        raise
