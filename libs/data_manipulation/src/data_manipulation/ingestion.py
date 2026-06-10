import io
import json
import logging
import re
import shutil
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlretrieve

import chardet
import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio
import pyogrio.raw
import requests
import shapely
from geoalchemy2 import Geometry
from sqlalchemy import MetaData, Table, select, text
from sqlalchemy.engine import Engine

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN, POSTGIS_TABLE_NAME_MAX_LENGTH
from data_manipulation.models import ColumnConfig, IntegrityTransformation
from data_manipulation.transformation.filter_sql import build_sql_column_ops
from data_manipulation.transformation.transform import apply_transformations
from data_manipulation.utils import resolve_url
from data_manipulation.validators import validate_schema_name, validate_table_name

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA = "public"
_ENCODING_DETECT_BYTES = 256 * 1024
_COPY_CHUNK_ROWS = 50_000
_READ_BATCH_ROWS = _COPY_CHUNK_ROWS


def _parquet_crs(pf: Any) -> object | None:
    """Best-effort CRS extraction from GeoParquet ``geo`` schema metadata.

    Returns whatever ``GeoDataFrame(crs=...)`` accepts (PROJJSON dict, EPSG
    string, or None). GeoParquet < 1.0 sometimes omitted CRS — default per the
    spec is OGC:CRS84 (lon/lat, EPSG:4326-equivalent).
    """
    md = pf.schema_arrow.metadata or {}
    raw = md.get(b"geo")
    if not raw:
        return None
    try:
        geo = json.loads(raw)
        primary = geo.get("primary_column", "geometry")
        col = geo.get("columns", {}).get(primary, {})
        crs = col.get("crs")
        if crs is None:
            return "OGC:CRS84"
        return crs
    except Exception as e:
        logger.warning(f"Failed to parse GeoParquet metadata: {e}")
        return None


def _iter_parquet_batches(
    file_path: str, batch_rows: int
) -> Iterator["gpd.GeoDataFrame | pd.DataFrame"]:
    """Yield bounded-memory batches from a (Geo)Parquet file."""

    pf = pq.ParquetFile(file_path)
    md = pf.schema_arrow.metadata or {}
    geo_meta_raw = md.get(b"geo")
    geom_col: str | None = None
    crs: object | None = None
    if geo_meta_raw:
        try:
            geo = json.loads(geo_meta_raw)
            geom_col = geo.get("primary_column", "geometry")
            crs = _parquet_crs(pf)
        except Exception:
            geom_col = None

    for record_batch in pf.iter_batches(batch_size=batch_rows):
        df = record_batch.to_pandas()
        if geom_col is not None and geom_col in df.columns:
            geometries = shapely.from_wkb(np.asarray(df[geom_col].values))
            tabular = df.drop(columns=[geom_col])
            yield gpd.GeoDataFrame(tabular, geometry=geometries, crs=crs)  # type: ignore[arg-type]
        else:
            yield df


def _iter_pyogrio_arrow_batches(
    file_path: str, batch_rows: int, *, layer: str | None = None
) -> Iterator["gpd.GeoDataFrame | pd.DataFrame"]:
    """Yield bounded-memory batches from any OGR-readable file via Arrow.

    Decodes WKB geometry per batch into a shapely-backed GeoDataFrame so the
    caller sees the same shape it would get from ``gpd.read_file``.
    """

    with pyogrio.raw.open_arrow(file_path, layer=layer, batch_size=batch_rows) as (meta, stream):
        crs = meta.get("crs")
        geom_name = meta.get("geometry_name") or "wkb_geometry"
        has_geom = bool(meta.get("geometry_type"))
        # pyogrio 0.10+ yields an _ArrowStream that exposes the C-stream
        # interface; wrap it so we can iterate RecordBatch by RecordBatch.
        reader = (
            stream
            if isinstance(stream, pa.RecordBatchReader)
            else pa.RecordBatchReader.from_stream(stream)
        )
        for record_batch in reader:
            df = pa.Table.from_batches([record_batch]).to_pandas()
            if has_geom and geom_name in df.columns:
                wkb_bytes = np.asarray(df[geom_name].values)
                geometries = shapely.from_wkb(wkb_bytes)
                tabular = df.drop(columns=[geom_name])
                yield gpd.GeoDataFrame(tabular, geometry=geometries, crs=crs)  # type: ignore[arg-type]
            else:
                yield df


def _iter_shapefile_encoded_batches(
    file_path: str, batch_rows: int
) -> Iterator["gpd.GeoDataFrame | pd.DataFrame"]:
    """Chunked fallback for legacy-encoded shapefiles.

    pyogrio's Arrow path can't always decode non-UTF-8 DBF attributes. Detect
    the encoding once, probe the feature count, then read in fixed-size
    windows with ``skip_features`` / ``max_features``. shapefile has a hard
    2 GB-per-file limit so this loop terminates cheaply.
    """
    encoding = _detect_file_encoding(file_path)
    info = pyogrio.read_info(file_path)
    total = int(info.get("features", 0) or 0)
    if total <= 0:
        return
    offset = 0
    while offset < total:
        batch = pyogrio.read_dataframe(
            file_path,
            encoding=encoding,
            skip_features=offset,
            max_features=batch_rows,
        )
        if len(batch) == 0:
            break
        yield batch
        offset += len(batch)


def _iter_data_batches(
    file_path: str,
    batch_rows: int = _READ_BATCH_ROWS,
) -> Iterator["gpd.GeoDataFrame | pd.DataFrame"]:
    """Yield bounded-memory batches from a geospatial or tabular file.

    Dispatch by extension. Each batch carries at most ``batch_rows`` rows, so
    peak memory is independent of file size. Returned objects are
    GeoDataFrames when the source has geometry, plain DataFrames otherwise.
    """
    suffix = Path(file_path).suffix.lower()

    if suffix in (".parquet", ".geoparquet"):
        yield from _iter_parquet_batches(file_path, batch_rows)
        return

    try:
        yield from _iter_pyogrio_arrow_batches(file_path, batch_rows)
        return
    except UnicodeDecodeError:
        if suffix != ".shp":
            raise
        logger.warning(
            "UTF-8 decode failed on %s; falling back to chunked non-Arrow read",
            file_path,
        )

    yield from _iter_shapefile_encoded_batches(file_path, batch_rows)


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

            _write_batches_to_postgis(
                _iter_data_batches(str(temp_file_path)),
                table_name,
                engine,
                schema,
            )

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
            response = requests.get(resolved_url, auth=auth, timeout=None, stream=True)
            response.raise_for_status()

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
                response.raw.decode_content = True
                with open(temp_file_path, "wb") as temp_file:
                    shutil.copyfileobj(response.raw, temp_file)

                _write_batches_to_postgis(
                    _iter_data_batches(str(temp_file_path)),
                    table_name,
                    engine,
                    schema,
                )
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
    validate_table_name(target_table)
    validate_schema_name(target_schema)

    logger.info(
        f"Ingesting data from {source_schema}.{source_table} into staging table {target_table}"
    )

    try:
        metadata = MetaData(schema=source_schema)
        source_tbl = Table(source_table, metadata, autoload_with=source_engine)

        geom_col = _get_geo_column_from_table(source_tbl)
        srid = 0
        if geom_col is not None:
            geom_type = source_tbl.c[geom_col].type
            if isinstance(geom_type, Geometry):
                srid = geom_type.srid or 0

        def _iter_source_batches() -> Iterator[gpd.GeoDataFrame | pd.DataFrame]:
            stream_conn = source_engine.connect().execution_options(
                stream_results=True, yield_per=_COPY_CHUNK_ROWS
            )
            try:
                chunk_iter = pd.read_sql(  # pyright: ignore[reportUnknownMemberType]
                    select(source_tbl), stream_conn, chunksize=_COPY_CHUNK_ROWS
                )
                for chunk in chunk_iter:
                    if geom_col is not None and geom_col in chunk.columns:
                        # Vectorised WKBElement → shapely: pull raw WKB bytes
                        # once, decode the whole column in one shapely call.
                        wkb_bytes = np.fromiter(
                            (v.data if v is not None else None for v in chunk[geom_col]),
                            dtype=object,
                            count=len(chunk),
                        )
                        chunk[geom_col] = shapely.from_wkb(wkb_bytes)
                        chunk = gpd.GeoDataFrame(
                            chunk,
                            geometry=geom_col,
                            crs=f"EPSG:{srid}" if srid else None,
                        )
                    yield chunk
            finally:
                stream_conn.close()

        _write_batches_to_postgis(
            _iter_source_batches(), target_table, target_engine, target_schema
        )
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
        _write_batches_to_postgis(
            _iter_pyogrio_arrow_batches(gdal_source, _READ_BATCH_ROWS, layer=layer_name),
            table_name,
            engine,
            schema,
        )
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


def _srid_from_crs(crs: object) -> int:
    """Best-effort SRID extraction for a (Geo)Series CRS. Returns 0 when unknown."""
    if crs is None:
        return 0
    try:
        epsg = crs.to_epsg()  # type: ignore[attr-defined]
    except Exception:
        return 0
    return int(epsg) if epsg is not None else 0


def _iter_csv_chunks(
    data: pd.DataFrame,
    geom_col: str | None,
    srid: int,
    chunk_rows: int = _COPY_CHUNK_ROWS,
) -> Iterator[bytes]:
    """Yield CSV-encoded byte chunks (one chunk = up to ``chunk_rows`` rows).

    Geometries in ``geom_col`` are vectorised once per chunk to EWKB hex
    (with SRID), so the geometry column lands on PostGIS as native ``geometry``
    via the implicit EWKB-hex text cast.
    """
    n = len(data)
    if n == 0:
        return

    for start in range(0, n, chunk_rows):
        chunk = data.iloc[start : start + chunk_rows]

        if geom_col is not None and geom_col in chunk.columns:
            geom_arr = chunk[geom_col].to_numpy()
            if srid:
                geom_arr = shapely.set_srid(geom_arr, srid)
            hex_arr = shapely.to_wkb(geom_arr, hex=True, include_srid=bool(srid))
            chunk = pd.DataFrame(chunk).assign(**{geom_col: hex_arr})

        buf = io.BytesIO()
        chunk.to_csv(
            buf,
            index=False,
            header=False,
            na_rep="",
            lineterminator="\n",
            encoding="utf-8",
        )
        yield buf.getvalue()


def _copy_bytes_to_postgres(
    table_name: str,
    schema: str,
    columns: list[str],
    chunks: Iterator[bytes],
    engine: Engine,
    *,
    raw_conn: Any | None = None,
) -> None:
    """Stream pre-encoded CSV byte chunks into an *existing* table via COPY.

    Caller is responsible for having created ``schema.table_name`` first.
    Supports both psycopg2 (Airflow PostgresHook) and psycopg3 (backend);
    the driver is dispatched on ``engine.dialect.driver``.

    When ``raw_conn`` is provided, the caller owns its lifecycle — we open a
    cursor on it for COPY and never commit/rollback/close. Otherwise a fresh
    raw connection is borrowed from the engine pool and managed here.
    """
    # Validate identifiers to prevent SQL injection
    validate_table_name(table_name, max_length=POSTGIS_TABLE_NAME_MAX_LENGTH)
    validate_schema_name(schema)

    col_list = ", ".join(f'"{c}"' for c in columns)
    fq_table = f'"{schema}"."{table_name}"'
    copy_sql = f"COPY {fq_table} ({col_list}) FROM STDIN WITH (FORMAT CSV, HEADER false, NULL '')"

    driver = engine.dialect.driver
    own_conn = raw_conn is None
    raw = engine.raw_connection() if own_conn else raw_conn
    try:
        cursor = raw.cursor()
        try:
            if driver == "psycopg":
                with cursor.copy(copy_sql) as copy:
                    for chunk in chunks:
                        copy.write(chunk)
            elif driver == "psycopg2":
                buffer = _ChunkedReadable(chunks)
                cursor.copy_expert(copy_sql, buffer)
            else:
                raise RuntimeError(
                    f"Unsupported postgres driver for COPY: {driver!r}. "
                    "Expected 'psycopg' or 'psycopg2'."
                )
        finally:
            cursor.close()
        if own_conn:
            raw.commit()
    except Exception:
        if own_conn:
            raw.rollback()
        raise
    finally:
        if own_conn:
            raw.close()


def _normalise_geometry_columns(
    data: "gpd.GeoDataFrame | pd.DataFrame",
) -> "tuple[gpd.GeoDataFrame | pd.DataFrame, str | None]":
    """Apply the ``geom``-column rules used historically by ``write_data_to_postgis``.

    Returns the (possibly-modified) frame and the geometry column name to use
    when streaming to PostGIS (``None`` for tabular output).
    """
    if not isinstance(data, gpd.GeoDataFrame):
        if DEFAULT_GEOMETRY_COLUMN in data.columns:
            logger.warning(
                f"DataFrame already has a '{DEFAULT_GEOMETRY_COLUMN}' column. "
                "Dropping it before writing to PostGIS."
            )
            data = data.drop(columns=[DEFAULT_GEOMETRY_COLUMN])
        return data, None

    if data.active_geometry_name is None:
        logger.info("GeoDataFrame has no active geometry column set.")
        if DEFAULT_GEOMETRY_COLUMN in data.columns:
            logger.warning(
                f"GeoDataFrame already has a '{DEFAULT_GEOMETRY_COLUMN}' column."
                " Dropping it before writing to PostGIS."
            )
            data = data.drop(columns=[DEFAULT_GEOMETRY_COLUMN])
        return data, None

    if data.active_geometry_name == DEFAULT_GEOMETRY_COLUMN:
        return data, DEFAULT_GEOMETRY_COLUMN

    # active geom under a non-default name
    if DEFAULT_GEOMETRY_COLUMN in data.columns:
        logger.warning(
            f"GeoDataFrame already has a '{DEFAULT_GEOMETRY_COLUMN}' column."
            " Overwriting it with the active geometry column."
        )
        return data, data.active_geometry_name
    logger.info(f"Renaming active geometry column to '{DEFAULT_GEOMETRY_COLUMN}'")
    data = data.rename_geometry(DEFAULT_GEOMETRY_COLUMN)
    return data, DEFAULT_GEOMETRY_COLUMN


def _write_batches_to_postgis(
    batches: "Iterator[gpd.GeoDataFrame | pd.DataFrame]",
    table_name: str,
    engine: Engine,
    schema: str = DEFAULT_SCHEMA,
    create_id: bool = False,
) -> int:
    """Stream a sequence of DataFrame batches into ``schema.table_name`` via COPY.

    DDL (table replacement) and all COPYs run inside a single transaction on
    a shared raw connection, so a mid-stream failure rolls the replacement
    back atomically. Returns the total number of rows written.
    """
    validate_table_name(table_name)
    validate_schema_name(schema)

    iterator = iter(batches)
    try:
        first = next(iterator)
    except StopIteration as e:
        raise ValueError("No data to write: batch iterator was empty.") from e

    first, geom_col = _normalise_geometry_columns(first)
    srid = 0
    if isinstance(first, gpd.GeoDataFrame) and geom_col is not None:
        srid = _srid_from_crs(first.crs)

    total_rows = 0
    columns = list(first.columns)
    fq_table = f'"{schema}"."{table_name}"'

    try:
        with engine.begin() as sa_conn:
            # Bootstrap target table with the right column types (1 DDL, no rows).
            empty = first.head(0)
            if isinstance(empty, gpd.GeoDataFrame) and geom_col is not None:
                empty.to_postgis(
                    table_name, sa_conn, if_exists="replace", schema=schema, index=False
                )
            else:
                if isinstance(empty, gpd.GeoDataFrame):
                    empty = pd.DataFrame(empty)
                empty.to_sql(table_name, sa_conn, if_exists="replace", schema=schema, index=False)

            raw_conn = sa_conn.connection  # type: ignore[attr-defined]

            def _process(batch: "gpd.GeoDataFrame | pd.DataFrame") -> int:
                normalised, _ = _normalise_geometry_columns(batch)
                _copy_bytes_to_postgres(
                    table_name,
                    schema,
                    columns,
                    _iter_csv_chunks(normalised, geom_col, srid),
                    engine,
                    raw_conn=raw_conn,
                )
                return len(normalised)

            total_rows += _process(first)
            for batch in iterator:
                total_rows += _process(batch)

            if create_id:
                sa_conn.execute(
                    text(
                        f"ALTER TABLE {fq_table} "
                        "ADD COLUMN id_datafeeder UUID DEFAULT gen_random_uuid() NOT NULL"
                    )
                )
                sa_conn.execute(text(f"ALTER TABLE {fq_table} ADD PRIMARY KEY (id_datafeeder)"))
                logger.info(
                    f"Added 'id_datafeeder' UUID primary key column to {schema}.{table_name}"
                )
    except Exception as e:
        logger.error(f"Error writing data to PostGIS table {schema}.{table_name}: {e}")
        raise

    logger.info(f"Successfully inserted {total_rows} rows into {schema}.{table_name}")
    return total_rows


class _ChunkedReadable(io.RawIOBase):
    """File-like adapter exposing a chunk iterator as a readable byte stream.

    psycopg2's ``copy_expert`` expects a file with ``read(size)``; we feed it
    chunks from our generator without ever materialising the full CSV.
    """

    # Trim the leading consumed slice once it exceeds this many bytes, to keep
    # the bytearray from growing without bound on long COPY streams.
    _TRIM_THRESHOLD = 1 << 20

    def __init__(self, chunks: Iterator[bytes]) -> None:
        super().__init__()
        self._chunks = chunks
        self._buf = bytearray()
        self._pos = 0

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            remaining = bytes(memoryview(self._buf)[self._pos :])
            self._buf = bytearray()
            self._pos = 0
            return remaining + b"".join(self._chunks)

        while len(self._buf) - self._pos < size:
            try:
                self._buf.extend(next(self._chunks))
            except StopIteration:
                break

        end = min(self._pos + size, len(self._buf))
        out = bytes(memoryview(self._buf)[self._pos : end])
        self._pos = end

        if self._pos >= self._TRIM_THRESHOLD:
            del self._buf[: self._pos]
            self._pos = 0

        return out
