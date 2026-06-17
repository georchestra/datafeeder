import logging
import re
import tempfile
from pathlib import Path
from typing import Literal
from urllib.error import URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlretrieve

import chardet
import geopandas as gpd
import pandas as pd
import requests
from geoalchemy2 import Geometry
from sqlalchemy import MetaData, Table, func, select, text
from sqlalchemy.engine import Engine

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN, POSTGIS_TABLE_NAME_MAX_LENGTH
from data_manipulation.models import ColumnConfig, IntegrityTransformation
from data_manipulation.transformation.filter_sql import build_sql_column_ops
from data_manipulation.transformation.transform import apply_transformations
from data_manipulation.utils import resolve_url
from data_manipulation.validators import validate_schema_name, validate_table_name

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA = "public"

# Bytes sampled for encoding detection. chardet's accuracy is unchanged for a sample
# this size, and reading only a sample avoids loading multi-GB files into memory.
_ENCODING_DETECT_BYTES = 256 * 1024
# Number of rows read and written to PostGIS per chunk. Keeps the memory footprint low
# (only one chunk is held in memory / converted to WKB at a time) for large files.
CHUNK_SIZE = 50000


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
    file_path_to_read = file_path
    path = Path(file_path)

    # GeoJSON must be UTF-8 according to RFC 7946
    if path.suffix.lower() in (".geojson", ".json"):
        return "utf-8"

    # Check for .cpg file (encoding file for shapefiles)
    if path.suffix.lower() == ".shp":
        cpg_file = path.with_suffix(".cpg")
        if cpg_file.exists():
            file_path_to_read = str(cpg_file)

    try:
        with open(file_path_to_read, "rb") as f:
            sample = f.read(_ENCODING_DETECT_BYTES)
        encoding = chardet.detect(sample)["encoding"]
    except Exception as e:
        logger.warning(f"Failed to detect encoding for {file_path_to_read}: {e}")
        encoding = None

    return encoding or "utf-8"


def _read_file_encoded(file_path: str, i: int = 0) -> gpd.GeoDataFrame | pd.DataFrame:
    """Read a chunk of a geospatial file, handling encoding detection.

    Reads ``CHUNK_SIZE`` rows starting at offset ``i * CHUNK_SIZE``. Returns an empty
    frame once the offset is past the end of the file, which lets callers iterate until
    the whole file has been ingested without ever loading it entirely in memory.

    Args:
        file_path: Path to the file
        i: Zero-based chunk index

    Returns:
        GeoDataFrame or DataFrame with the chunk data (empty when there is no more data)
    """
    rows = slice(i * CHUNK_SIZE, i * CHUNK_SIZE + CHUNK_SIZE, None)
    # Parquet is columnar and not row-sliceable cheaply: read it fully on the first
    # chunk and signal completion afterwards to avoid re-reading / duplicating rows.
    if Path(file_path).suffix.lower() in (".parquet", ".geoparquet"):
        if i > 0:
            return gpd.GeoDataFrame()
        try:
            return gpd.read_parquet(file_path)  # type: ignore[arg-type]
        except ValueError:
            return pd.read_parquet(file_path)

    try:
        # Try reading with UTF-8 first (common default)
        return gpd.read_file(file_path, rows=rows)  # type: ignore[arg-type]
    except UnicodeDecodeError:
        logger.warning(
            "Failed to read file with UTF-8 encoding, attempting to detect encoding and read again."
        )

    # Detect encoding (mainly for shapefiles, others default to UTF-8)
    encoding = _detect_file_encoding(file_path)
    logger.warning("Detected encoding: %s", encoding)
    return gpd.read_file(file_path, rows=rows, encoding=encoding)  # type: ignore[arg-type]


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
        # Read data with encoding handling, use the url function,
        # the path to the file is always an url, even for local files
        ingest_data_from_url_into_postgis(file_path, table_name, engine, schema)
    except Exception as e:
        logger.error(f"Error ingesting data from file {file_path}: {e}")
        raise


def ingest_data_from_ftp_into_postgis(
    url: str,
    table_name: str,
    engine: Engine,
    schema: str = DEFAULT_SCHEMA,
    auth: tuple[str, str] | None = None,
) -> None:
    """Ingest data from an FTP URL into a PostGIS table.

    Args:
        url: FTP URL to download data from
        table_name: Target table name in PostGIS
        engine: SQLAlchemy engine
        schema: Target schema (default: public)
        auth: Optional tuple of (username, password) for FTP authentication
    """
    logger.info(f"Ingesting data from FTP {url} into table {table_name}")

    parsed_url = urlparse(url)

    # Build FTP URL with credentials if provided
    if auth:
        username, password = auth

        # URL-encode username and password to handle special characters
        encoded_username = quote(username, safe="")
        encoded_password = quote(password, safe="")

        # Reconstruct URL with credentials
        netloc_with_auth = f"{encoded_username}:{encoded_password}@{parsed_url.netloc}"
        ftp_url_with_auth = f"{parsed_url.scheme}://{netloc_with_auth}{parsed_url.path}"
    else:
        ftp_url_with_auth = url

    # --------
    # WARNING: don't log ftp_url_with_auth as it may contain sensitive credentials
    # --------

    # Extract filename from path
    filename = Path(parsed_url.path).name

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = Path(temp_dir) / filename

            # Download FTP file using urlretrieve
            urlretrieve(ftp_url_with_auth, temp_file_path)

            i = 0
            while True:
                data = _read_file_encoded(str(temp_file_path), i)
                if data.empty:
                    break
                write_data_to_postgis(
                    data, table_name, engine, schema, if_exists="replace" if i == 0 else "append"
                )
                logger.debug(
                    "Ingested chunk %s (%s rows) from FTP %s into table %s",
                    i,
                    len(data),
                    url,
                    table_name,
                )
                # A short read means the file is exhausted — avoid an extra empty read.
                if len(data) < CHUNK_SIZE:
                    break
                i += 1

    # TODO: handle error for frontend
    except URLError as e:
        # --------
        # WARNING: don't log ftp_url_with_auth as it may contain sensitive credentials
        # --------

        # Handle FTP-specific errors
        error_msg = str(e.reason) if hasattr(e, "reason") else str(e)

        if "530" in error_msg or "Login incorrect" in error_msg:
            logger.error(f"FTP authentication failed for {url}: {error_msg}")
            raise Exception("FTP authentication failed: Invalid username or password")
        elif "550" in error_msg or "No such file" in error_msg:
            logger.error(f"FTP file not found: {url}")
            raise Exception(f"FTP file not found: {parsed_url.path}")
        elif "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
            logger.error(f"FTP connection timeout for {url}: {error_msg}")
            raise Exception(f"FTP connection timeout: Unable to reach server {parsed_url.netloc}")
        elif "Connection refused" in error_msg:
            logger.error(f"FTP connection refused for {url}: {error_msg}")
            raise Exception(f"FTP connection refused: Server {parsed_url.netloc} is not accessible")
        else:
            logger.error(f"FTP error for {url}: {error_msg}")
            raise Exception(f"FTP error: {error_msg}")
    except OSError as e:
        logger.error(f"Network error while accessing FTP {url}: {e}")
        raise Exception(f"Network error: Unable to connect to FTP server {parsed_url.netloc}")
    except Exception as e:
        logger.error(f"Error ingesting data from FTP {url}: {e}")
        raise


def _get_geo_column_from_table(table: Table) -> str | None:
    """Return default geometry column or the name of the first geometry column found in a table."""
    if DEFAULT_GEOMETRY_COLUMN in table.c and isinstance(
        table.c[DEFAULT_GEOMETRY_COLUMN], Geometry
    ):
        return DEFAULT_GEOMETRY_COLUMN
    for column in table.columns:
        if isinstance(column.type, Geometry):
            logger.debug("Found geom column in source table: %s", column.name)
            return column.name
    return None


def ingest_data_from_url_into_postgis(
    url: str,
    table_name: str,
    engine: Engine,
    schema: str = DEFAULT_SCHEMA,
    auth: tuple[str, str] | None = None,
) -> None:
    """Ingest data from a URL into a PostGIS table.

    Args:
        url: URL to download data from (supports HTTP, HTTPS, and FTP)
        table_name: Target table name in PostGIS
        engine: SQLAlchemy engine
        schema: Target schema (default: public)
        auth: Optional tuple of (username, password) for HTTP Basic Authentication or FTP
    """
    try:
        # Download file first (GeoPandas doesn't support Basic Auth natively + better handle file types)
        logger.info(f"Ingesting data from url {url} into table {table_name}")

        parsed_url = urlparse(url)

        # Handle FTP URLs separately
        if parsed_url.scheme == "ftp":
            ingest_data_from_ftp_into_postgis(url, table_name, engine, schema, auth)
        else:
            # Use requests for HTTP/HTTPS URLs
            resolved_url = resolve_url(url)
            response = requests.get(resolved_url, auth=auth, timeout=300)
            response.raise_for_status()
            content = response.content

            content_disposition = response.headers.get("Content-Disposition")
            filename = None

            if content_disposition:
                # e.g. 'attachment; filename="report.csv"'
                for part in content_disposition.split(";"):
                    part = part.strip()
                    if part.startswith("filename="):
                        filename = part.split("=", 1)[1].strip('"')
                        filename = unquote(filename)

                logger.info(f"Extracted filename from Content-Disposition: {filename}")

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_file_path = Path(temp_dir) / (
                    filename or Path(urlparse(resolved_url).path).name
                )
                with open(temp_file_path, "wb") as temp_file:
                    temp_file.write(content)

                i = 0
                while True:
                    data = _read_file_encoded(str(temp_file_path), i)
                    if data.empty:
                        break
                    write_data_to_postgis(
                        data,
                        table_name,
                        engine,
                        schema,
                        if_exists="replace" if i == 0 else "append",
                    )
                    logger.debug(
                        "Ingested chunk %s (%s rows) from URL %s into table %s",
                        i,
                        len(data),
                        url,
                        table_name,
                    )
                    # A short read means the file is exhausted — avoid an extra empty read.
                    if len(data) < CHUNK_SIZE:
                        break
                    i += 1
    except Exception as e:
        logger.error(f"Error ingesting data from URL {url}: {e}")
        raise


def ingest_data_from_database_into_postgis(
    source_schema: str,
    source_table: str,
    source_engine: Engine,
    target_table: str,
    target_engine: Engine,
    target_schema: str = DEFAULT_SCHEMA,
) -> None:
    """Ingest data from a PostgreSQL table into a PostGIS staging table.

    Args:
        source_schema: Schema name in the source database
        source_table: Table name in the source database
        source_engine: SQLAlchemy engine for the source database
        target_table: Target table name in the staging database
        target_engine: SQLAlchemy engine for the staging (data) database
        target_schema: Target schema (default: public)
    """
    validate_schema_name(source_schema)
    validate_table_name(source_table)

    logger.info(
        f"Ingesting data from {source_schema}.{source_table} into staging table {target_table}"
    )

    try:
        metadata = MetaData(schema=source_schema)
        table = Table(source_table, metadata, autoload_with=source_engine)

        geom = _get_geo_column_from_table(table)

        # A stable ORDER BY is required so that LIMIT/OFFSET pagination returns each row
        # exactly once. Prefer the primary key; fall back to all columns when absent.
        order_columns = list(table.primary_key.columns) or list(table.columns)
        base_query = select(table).order_by(*order_columns)

        # Read and write one chunk at a time to keep the memory footprint low for large tables.
        i = 0
        while True:
            query = base_query.limit(CHUNK_SIZE).offset(i * CHUNK_SIZE)
            if geom is not None:
                data = gpd.read_postgis(query, con=source_engine, geom_col=geom)  # type: ignore[call-overload]
            else:
                data = pd.read_sql(query, source_engine)
            if data.empty:
                break

            write_data_to_postgis(
                data,
                target_table,
                target_engine,
                target_schema,
                if_exists="replace" if i == 0 else "append",
            )
            logger.debug(
                "Ingested chunk %s (%s rows) from table %s into table %s",
                i,
                len(data),
                source_table,
                target_table,
            )

            # A short read means we have reached the end of the table — avoid an extra empty query.
            if len(data) < CHUNK_SIZE:
                break
            i += 1

    except Exception as e:
        logger.error(f"Error ingesting data from {source_schema}.{source_table}: {e}")
        raise


_GDAL_PROTOCOL_PREFIX = {"wfs": "WFS", "ogcFeatures": "OAPIF"}
_OAPIF_COLLECTIONS_RE = re.compile(r"/collections(/.*)?$")


def _normalize_oapif_url(url: str) -> str:
    """Strip /collections[/...] suffixes so GDAL's OAPIF driver receives the service root."""
    return _OAPIF_COLLECTIONS_RE.sub("", url.rstrip("/"))


def ingest_data_from_ogc_service_into_postgis(
    service_url: str,
    layer_name: str,
    protocol: str,
    table_name: str,
    engine: Engine,
    schema: str = DEFAULT_SCHEMA,
) -> None:
    """Ingest a WFS or OGC API Features layer into PostGIS using GeoPandas/GDAL.

    `protocol` is the service protocol as stored: 'wfs' or 'ogcFeatures'.
    The GDAL driver prefix (WFS: / OAPIF:) is built internally.

    `layer_name` maps directly to the GDAL layer name in both cases:
    - WFS: the WFS typename (e.g. "ns:buildings"), set as identifierInService by geonetwork-ui
    - OAPIF: the collection ID (e.g. "buildings"), the `name` from OgcApiEndpoint.allCollections
    No additional parameters are needed beyond layer=layer_name for basic ingestion.
    """
    gdal_prefix = _GDAL_PROTOCOL_PREFIX.get(protocol, "WFS")
    normalized_url = _normalize_oapif_url(service_url) if protocol == "ogcFeatures" else service_url
    gdal_source = f"{gdal_prefix}:{normalized_url}"
    logger.info(f"Ingesting OGC layer '{layer_name}' from {gdal_source} into {table_name}")
    try:
        i = 0
        while True:
            rows = slice(i * CHUNK_SIZE, i * CHUNK_SIZE + CHUNK_SIZE, None)
            gdf = gpd.read_file(gdal_source, layer=layer_name, rows=rows)
            if gdf.empty:
                break
            chunk_len = len(gdf)
            # OGC API Features collections may have no geometry — treat as tabular data in that case
            data: gpd.GeoDataFrame | pd.DataFrame = gdf
            if gdf.geometry.isna().all():
                logger.info(
                    f"Layer '{layer_name}' has no valid geometries; ingesting as tabular data."
                )
                data = pd.DataFrame(gdf.drop(columns=str(gdf.geometry.name)))
            write_data_to_postgis(
                data, table_name, engine, schema, if_exists="replace" if i == 0 else "append"
            )
            logger.debug(
                "Ingested chunk %s (%s rows) from OGC service %s into table %s",
                i,
                chunk_len,
                gdal_source,
                table_name,
            )
            # A short read means the layer is exhausted — avoid an extra empty request.
            if chunk_len < CHUNK_SIZE:
                break
            i += 1
    except Exception as e:
        logger.error(f"Error ingesting OGC layer '{layer_name}' from {gdal_source}: {e}")
        raise


def read_data_from_postgis(
    table_name: str,
    engine: Engine,
    schema: str | None = None,
    limit: int | None = None,
    columns: list[ColumnConfig] | None = None,
) -> pd.DataFrame:
    """Read data from a PostGIS table.

    When *columns* is provided, exclusion and filtering are applied at the SQL
    level so that WHERE clauses execute *before* any LIMIT.  The resulting
    SQLAlchemy ``Select`` object is passed directly to ``gpd.read_postgis`` /
    ``pd.read_sql`` — never compiled to a string — so all filter values remain
    bound parameters (no SQL injection risk).

    Args:
        table_name: Name of the table to read.
        engine: SQLAlchemy engine.
        schema: PostgreSQL schema name (optional).
        limit: Maximum number of rows to return (applied after filters).
        columns: Optional list of column configurations.  When provided,
            excluded columns are omitted from the SELECT and active filters are
            applied as WHERE clauses.  When ``None``, all columns are returned
            without filtering.

    Returns:
        GeoDataFrame or DataFrame containing the (filtered) table data.
    """
    # Validate identifiers to prevent SQL injection
    validate_table_name(table_name)
    if schema:
        validate_schema_name(schema)

    try:
        # Use SQLAlchemy Core to safely construct the query
        metadata = MetaData(schema=schema)
        table = Table(table_name, metadata, autoload_with=engine)

        if columns is not None:
            select_cols, where_clauses = build_sql_column_ops(columns, table)

            if not select_cols:
                # All columns excluded — return an empty DataFrame immediately
                logger.warning(
                    f"All columns excluded for table {schema}.{table_name}, returning empty DataFrame"
                )
                return pd.DataFrame()

            query = select(*select_cols)
            if where_clauses:
                query = query.where(*where_clauses)

            has_geom = any(col.key == DEFAULT_GEOMETRY_COLUMN for col in select_cols)
        else:
            query = select(table)
            has_geom = DEFAULT_GEOMETRY_COLUMN in table.c

        if limit is not None and limit > 0:
            query = query.limit(limit)

        # Pass the Select object directly — both pd.read_sql and gpd.read_postgis
        # accept a SQLAlchemy Selectable natively in SQLAlchemy 2.x.
        # This guarantees that all filter values remain bound parameters.
        if has_geom:
            return gpd.read_postgis(query, con=engine, geom_col=DEFAULT_GEOMETRY_COLUMN)  # type: ignore[call-overload]
        else:
            return pd.read_sql(query, engine)
    except Exception as e:
        logger.error(f"Error reading data from PostGIS table {schema}.{table_name}: {e}")
        raise


def read_and_transform_data(
    table_name: str,
    engine: Engine,
    schema: str | None = None,
    config: IntegrityTransformation | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """Single pipeline entry point: read data and apply all transformations.

    Combines ``read_data_from_postgis`` (SQL-level exclusion + filtering) with
    ``apply_transformations`` (in-memory rename, cast, projection) in one call.

    Both the backend GET preview (``limit=10``, config from DB) and the Airflow
    process DAG (``limit=None``, config from DAG params) call this function
    identically, which is the architectural guarantee for FR-021 consistency.

    Args:
        table_name: Name of the staging table.
        engine: SQLAlchemy engine.
        schema: PostgreSQL schema name (optional).
        config: Transformation configuration.  ``None`` = return raw data
            unchanged (no column filtering, no transformations).
        limit: Row limit (``None`` = all rows).

    Returns:
        Transformed GeoDataFrame or DataFrame.
    """
    columns = config.columns if config is not None else None
    data = read_data_from_postgis(table_name, engine, schema=schema, limit=limit, columns=columns)

    if config is None:
        return data

    return apply_transformations(data, config)


def write_data_to_postgis(
    data: gpd.GeoDataFrame | pd.DataFrame,
    table_name: str,
    engine: Engine,
    schema: str = DEFAULT_SCHEMA,
    create_id: bool = False,
    if_exists: Literal["fail", "replace", "append"] = "replace",
) -> None:
    """Write a GeoDataFrame or DataFrame to a PostGIS table.

    Args:
        data: GeoDataFrame or DataFrame to write
        table_name: Name of the target table
        engine: SQLAlchemy engine
        schema: PostgreSQL schema name (optional)
        create_id: If True, add an 'id_datafeeder' UUID column as primary key
    """
    # Validate identifiers to prevent SQL injection
    validate_table_name(table_name, max_length=POSTGIS_TABLE_NAME_MAX_LENGTH)
    validate_schema_name(schema)

    try:
        if not isinstance(data, gpd.GeoDataFrame):  # DataFrame
            # Ensure there is no geom column
            if DEFAULT_GEOMETRY_COLUMN in data.columns:
                logger.warning(
                    f"DataFrame already has a '{DEFAULT_GEOMETRY_COLUMN}' column. Dropping it before writing to PostGIS."
                )
                data.drop(columns=[DEFAULT_GEOMETRY_COLUMN], inplace=True)

            # Write data to PostGIS as a regular table
            data.to_sql(table_name, engine, if_exists=if_exists, schema=schema, index=False)
        else:  # GeoDataFrame
            # Ensure the geometry column is named 'geom' for PostGIS convention
            if data.active_geometry_name is None:
                logger.info("GeoDataFrame has no active geometry column set.")

                # Ensure there is no geom column
                if DEFAULT_GEOMETRY_COLUMN in data.columns:
                    logger.warning(
                        f"GeoDataFrame already has a '{DEFAULT_GEOMETRY_COLUMN}' column."
                        " Dropping it before writing to PostGIS."
                    )
                    data.drop(columns=[DEFAULT_GEOMETRY_COLUMN], inplace=True)

            elif data.active_geometry_name == DEFAULT_GEOMETRY_COLUMN:
                logger.info(
                    f"GeoDataFrame has '{DEFAULT_GEOMETRY_COLUMN}' as active geometry column."
                )
            else:
                logger.info(
                    f"GeoDataFrame has '{data.active_geometry_name}' as active geometry column."
                )

                if DEFAULT_GEOMETRY_COLUMN in data.columns:
                    logger.warning(
                        f"GeoDataFrame already has a '{DEFAULT_GEOMETRY_COLUMN}' column."
                        " Overwriting it with the active geometry column."
                    )
                else:
                    logger.info(f"Renaming active geometry column to '{DEFAULT_GEOMETRY_COLUMN}'")
                    data.rename_geometry(DEFAULT_GEOMETRY_COLUMN, inplace=True)

            # Write data to PostGIS
            data.to_postgis(table_name, engine, if_exists=if_exists, schema=schema, index=False)

        if create_id:
            with engine.connect() as conn:
                conn.execute(
                    text(
                        f'ALTER TABLE "{schema}"."{table_name}" '
                        f"ADD COLUMN id_datafeeder UUID DEFAULT gen_random_uuid() NOT NULL"
                    )
                )
                conn.execute(
                    text(f'ALTER TABLE "{schema}"."{table_name}" ADD PRIMARY KEY (id_datafeeder)')
                )
                conn.commit()
            logger.info(f"Added 'id_datafeeder' UUID primary key column to {schema}.{table_name}")

        # Log the number of inserted rows
        row_count = _get_table_row_count(table_name, engine, schema)
        logger.info(f"Successfully inserted {row_count} rows into {schema}.{table_name}")
    except Exception as e:
        logger.error(f"Error writing data to PostGIS table {schema}.{table_name}: {e}")
        raise
