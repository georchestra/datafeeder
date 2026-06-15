import logging
import re
import shutil
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import urlretrieve

import requests
from sqlalchemy.engine import Engine

from data_manipulation.arrow_reader import (
    detect_file_encoding,
    open_file,
    open_ogr,
    open_postgis_table,
)
from data_manipulation.postgis_writer import write_arrow_to_postgis
from data_manipulation.utils import resolve_url
from data_manipulation.validators import validate_schema_name, validate_table_name

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA = "public"
_HTTP_TIMEOUT = (10, 300)


def _ingest_local_file(path: str, table_name: str, engine: Engine, schema: str) -> int:
    """Ingest a downloaded local file, retrying shapefiles with a detected encoding.

    The first attempt is rolled back by the writer on failure, so the
    encoding-aware retry is a clean full restart.
    """
    try:
        with open_file(path) as src:
            return write_arrow_to_postgis(src, table_name, engine, schema=schema)
    except UnicodeDecodeError:
        if Path(path).suffix.lower() != ".shp":
            raise
        encoding = detect_file_encoding(path)
        logger.warning(
            "UTF-8 decode failed on %s; retrying full ingest with encoding=%s", path, encoding
        )
        with open_file(path, encoding=encoding) as src:
            return write_arrow_to_postgis(src, table_name, engine, schema=schema)


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

            _ingest_local_file(str(temp_file_path), table_name, engine, schema)

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
            response = requests.get(resolved_url, auth=auth, timeout=_HTTP_TIMEOUT, stream=True)
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

                _ingest_local_file(str(temp_file_path), table_name, engine, schema)
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
        with open_postgis_table(source_table, source_schema, source_engine) as src:
            write_arrow_to_postgis(src, target_table, target_engine, schema=target_schema)
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
    """Ingest a WFS or OGC API Features layer into PostGIS using GDAL.

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
        with open_ogr(gdal_source, layer=layer_name) as src:
            write_arrow_to_postgis(src, table_name, engine, schema=schema)
    except Exception as e:
        logger.error(f"Error ingesting OGC layer '{layer_name}' from {gdal_source}: {e}")
        raise
