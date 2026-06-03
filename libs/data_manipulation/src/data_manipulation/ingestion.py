import logging
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlretrieve

import requests
from sqlalchemy.engine import Engine

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN, POSTGIS_TABLE_NAME_MAX_LENGTH
from data_manipulation.utils import resolve_url
from data_manipulation.validators import validate_schema_name, validate_table_name

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA = "public"


def _build_pg_connection_string(engine: Engine) -> str:
    """Build a GDAL ``PG:`` connection string from a SQLAlchemy engine.

    WARNING: the returned string embeds the database password — never log it.
    """
    url = engine.url
    pg_conn_parts = [
        f"host={url.host}",
        f"port={url.port or 5432}",
        f"dbname={url.database}",
        f"user={url.username}",
        f"password={url.password}",
    ]
    return "PG:" + " ".join(part for part in pg_conn_parts if part.split("=", 1)[1])


def _run_ogr2ogr(command: list[str], *, context: str) -> None:
    """Run an ogr2ogr command, raising a clean error on failure.

    WARNING: never log *command* itself — it may contain a ``PG:`` connection
    string or ``GDAL_HTTP_USERPWD`` credentials.
    """
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        logger.error("ogr2ogr binary not found while %s", context)
        raise Exception("ogr2ogr (GDAL) is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        logger.error("ogr2ogr failed while %s: %s", context, exc.stderr)
        raise Exception(f"ogr2ogr failed: {exc.stderr}")


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

            ingest_file_with_ogr2ogr(str(temp_file_path), table_name, engine, schema)

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


def ingest_file_with_ogr2ogr(
    file_path: str,
    table_name: str,
    engine: Engine,
    schema: str = DEFAULT_SCHEMA,
) -> None:
    """Ingest a geospatial file into a PostGIS table using ogr2ogr.

    Args:
        file_path: Path to the local file to ingest
        table_name: Target table name in PostGIS
        engine: SQLAlchemy engine for the target PostGIS database
        schema: Target schema (default: public)
    """
    validate_table_name(table_name, max_length=POSTGIS_TABLE_NAME_MAX_LENGTH)
    validate_schema_name(schema)

    pg_connection = _build_pg_connection_string(engine)

    command = [
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        pg_connection,
        file_path,
        "-nln",
        f"{schema}.{table_name}",
        "-overwrite",
        "-lco",
        f"GEOMETRY_NAME={DEFAULT_GEOMETRY_COLUMN}",
        "-lco",
        f"SCHEMA={schema}",
    ]

    logger.info(f"Running ogr2ogr to ingest {file_path} into {schema}.{table_name}")

    # --------
    # WARNING: don't log the command as the PG connection string contains credentials
    # --------
    _run_ogr2ogr(command, context=f"ingesting {file_path} into {schema}.{table_name}")


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

                start = time.time()

                ingest_file_with_ogr2ogr(str(temp_file_path), table_name, engine, schema)

                # Calculate the end time and time taken
                end = time.time()
                length = end - start

                print("It took", length, "seconds.")

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
    validate_schema_name(target_schema)
    validate_table_name(target_table, max_length=POSTGIS_TABLE_NAME_MAX_LENGTH)

    logger.info(
        f"Ingesting data from {source_schema}.{source_table} into staging table {target_table}"
    )

    source_connection = _build_pg_connection_string(source_engine)
    target_connection = _build_pg_connection_string(target_engine)

    command = [
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        target_connection,
        source_connection,
        f"{source_schema}.{source_table}",
        "-nln",
        f"{target_schema}.{target_table}",
        "-overwrite",
        "-lco",
        f"GEOMETRY_NAME={DEFAULT_GEOMETRY_COLUMN}",
        "-lco",
        f"SCHEMA={target_schema}",
    ]

    # --------
    # WARNING: don't log the command — both PG connection strings contain credentials
    # --------
    _run_ogr2ogr(
        command,
        context=f"ingesting {source_schema}.{source_table} into {target_schema}.{target_table}",
    )


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
    auth: tuple[str, str] | None = None,
) -> None:
    """Ingest a WFS or OGC API Features layer into PostGIS using ogr2ogr/GDAL.

    `protocol` is the service protocol as stored: 'wfs' or 'ogcFeatures'.
    The GDAL driver prefix (WFS: / OAPIF:) is built internally.

    `layer_name` maps directly to the GDAL layer name in both cases:
    - WFS: the WFS typename (e.g. "ns:buildings"), set as identifierInService by geonetwork-ui
    - OAPIF: the collection ID (e.g. "buildings"), the `name` from OgcApiEndpoint.allCollections

    `auth`, when provided, is an (username, password) tuple passed to GDAL as
    HTTP Basic credentials via the GDAL_HTTP_USERPWD config option.
    """
    gdal_prefix = _GDAL_PROTOCOL_PREFIX.get(protocol, "WFS")
    normalized_url = _normalize_oapif_url(service_url) if protocol == "ogcFeatures" else service_url
    gdal_source = f"{gdal_prefix}:{normalized_url}"
    logger.info(f"Ingesting OGC layer '{layer_name}' from {gdal_source} into {table_name}")

    validate_table_name(table_name, max_length=POSTGIS_TABLE_NAME_MAX_LENGTH)
    validate_schema_name(schema)

    pg_connection = _build_pg_connection_string(engine)

    command = [
        "ogr2ogr",
        "-f",
        "PostgreSQL",
        pg_connection,
        gdal_source,
        layer_name,
        "-nln",
        f"{schema}.{table_name}",
        "-overwrite",
        "-lco",
        f"GEOMETRY_NAME={DEFAULT_GEOMETRY_COLUMN}",
        "-lco",
        f"SCHEMA={schema}",
    ]

    if auth is not None:
        username, password = auth
        # --------
        # WARNING: don't log the command — GDAL_HTTP_USERPWD contains credentials
        # --------
        command += ["--config", "GDAL_HTTP_USERPWD", f"{username}:{password}"]

    _run_ogr2ogr(command, context=f"ingesting OGC layer '{layer_name}' into {schema}.{table_name}")
