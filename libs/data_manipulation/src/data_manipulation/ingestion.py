import logging
import os
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Literal
from urllib.error import URLError
from urllib.parse import quote, unquote, urlencode, urlparse, urlunparse
from urllib.request import urlretrieve

import chardet
import requests
from sqlalchemy.engine import Engine

from data_manipulation.constants import (
    DEFAULT_GEOMETRY_COLUMN,
    DEFAULT_OGC_SRS,
    POSTGIS_TABLE_NAME_MAX_LENGTH,
)
from data_manipulation.utils import resolve_url
from data_manipulation.validators import validate_schema_name, validate_table_name

logger = logging.getLogger(__name__)

DEFAULT_SCHEMA = "public"

# Bytes sampled for encoding detection. chardet's accuracy is unchanged for a sample
# this size, and reading only a sample avoids loading multi-GB files into memory.
_ENCODING_DETECT_BYTES = 256 * 1024
# Number of rows read and written to PostGIS per chunk. Keeps the memory footprint low
# (only one chunk is held in memory / converted to WKB at a time) for large files.
CHUNK_SIZE = int(os.getenv("DATAFEEDER_CHUNK_SIZE", 50000))
# Bytes read per iteration when streaming an HTTP download to disk.
_DOWNLOAD_CHUNK_SIZE = 1024 * 1024
# GDAL error lines, e.g. "ERROR 1: Non UTF-8 content found ...". Anchored at the
# start of a line so a path or attribute value containing "error" doesn't match.
_OGR_ERROR_RE = re.compile(r"^ERROR\s+\d+:", re.MULTILINE)
# Single-byte Latin codepages chardet confuses with CP1252 on short samples.
_WESTERN_LATIN_FALLBACK = frozenset(
    {"cp1250", "windows1250", "iso88592", "iso88591", "latin1", "maccentraleurope"}
)
# Shapefile sidecar files. Only the .shp names the dataset; the others accompany
# it and must not be counted as separate datasets inside an archive.
_SHAPEFILE_SIDECAR_SUFFIXES = frozenset(
    {".shx", ".dbf", ".prj", ".cpg", ".sbn", ".sbx", ".qix", ".fbn", ".fbx", ".ain", ".aih"}
)


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
        # errors="replace": ogr2ogr echoes the offending record when it rejects
        # non-UTF-8 input, so stderr itself may not be valid UTF-8. Strict decoding
        # would raise UnicodeDecodeError here and hide GDAL's actual message.
        result = subprocess.run(
            command, check=True, capture_output=True, text=True, errors="replace"
        )
    except FileNotFoundError as exc:
        logger.error("ogr2ogr binary not found while %s", context)
        raise Exception("ogr2ogr (GDAL) is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        logger.error("ogr2ogr failed while %s: %s", context, exc.stderr)
        raise Exception(f"ogr2ogr failed: {exc.stderr}") from exc

    # ogr2ogr exits 0 even when it aborts a layer translation (e.g. "ERROR 1: Non
    # UTF-8 content found when writing feature"), so check=True alone would report
    # success while no table was created.
    stderr = result.stderr or ""
    if _OGR_ERROR_RE.search(stderr):
        logger.error("ogr2ogr reported an error while %s: %s", context, stderr)
        raise Exception(f"ogr2ogr failed: {stderr}")


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


def _dbf_text_payload(dbf_bytes: bytes) -> bytes:
    """Return the record section of a ``.dbf``, skipping its binary header.

    chardet classifies a whole ``.dbf`` as ``application/octet-stream`` and gives
    up, because the fixed-width header and field descriptors drown out the few
    accented bytes. Feeding it only the records makes detection work.

    Falls back to the whole buffer when the header length is implausible.
    """
    # Bytes 8..10 of the DBF header hold the header length (little-endian uint16).
    if len(dbf_bytes) < 12:
        return dbf_bytes
    header_length = int.from_bytes(dbf_bytes[8:10], "little")
    if not 0 < header_length < len(dbf_bytes):
        return dbf_bytes
    # Drop the 0x1A end-of-file marker: chardet treats that control byte as a sign
    # of binary content and gives up on an otherwise perfectly readable payload.
    return dbf_bytes[header_length:].rstrip(b"\x1a")


def _detect_shapefile_encoding(file_path: str) -> str | None:
    """Guess the encoding of a shapefile's ``.dbf``, or ``None`` when not needed.

    GDAL reads the ``.cpg`` sidecar natively and assumes UTF-8 when it is absent.
    A shapefile shipped without a ``.cpg`` but encoded in e.g. CP1252 — common for
    French data — then makes ogr2ogr abort with "Non UTF-8 content found". Sample
    the ``.dbf`` and let chardet guess so the caller can pass SHAPE_ENCODING.

    Returns ``None`` when the source is not a shapefile, already carries a
    ``.cpg``, or when nothing could be detected — in all those cases GDAL's own
    handling is correct and must not be overridden.
    """
    members = _shapefile_members(file_path)
    if members is None:
        return None
    cpg_bytes, dbf_bytes = members
    # A .cpg is authoritative and GDAL already honours it.
    if cpg_bytes is not None or dbf_bytes is None:
        return None

    try:
        detected = chardet.detect(_dbf_text_payload(dbf_bytes))["encoding"]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to detect shapefile encoding: %s", exc)
        return None

    if not detected:
        return None

    normalized = detected.lower().replace("-", "").replace("_", "")
    if normalized in ("utf8", "ascii"):
        # ASCII is a subset of UTF-8, so GDAL's default already reads it correctly.
        return None

    # On the short samples a .dbf provides, chardet routinely cannot tell the
    # single-byte Latin codepages apart and returns a Central/Eastern European one
    # (cp1250, iso-8859-2, ...) for Western European text — which decodes 'ê' as
    # 'ę'. They agree on most of the range, so collapse them onto CP1252, the
    # encoding shapefiles without a .cpg overwhelmingly use in Western Europe.
    if normalized in _WESTERN_LATIN_FALLBACK:
        logger.info(
            "No .cpg alongside the shapefile; chardet guessed %s, using CP1252 instead",
            detected,
        )
        return "CP1252"

    logger.info("No .cpg alongside the shapefile; detected encoding %s", detected)
    return detected


def _shapefile_members(file_path: str) -> tuple[bytes | None, bytes | None] | None:
    """Return ``(cpg_bytes, dbf_sample)`` for a shapefile, or ``None`` if not one.

    Handles both a plain ``.shp`` on disk and a shapefile inside a ZIP, so the
    encoding of zipped shapefiles can be detected without extracting them.
    """
    if zipfile.is_zipfile(file_path):
        with zipfile.ZipFile(file_path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            if not any(name.lower().endswith(".shp") for name in names):
                return None
            cpg = next((n for n in names if n.lower().endswith(".cpg")), None)
            dbf = next((n for n in names if n.lower().endswith(".dbf")), None)
            cpg_bytes = archive.read(cpg) if cpg else None
            dbf_bytes = None
            if dbf:
                with archive.open(dbf) as handle:
                    dbf_bytes = handle.read(_ENCODING_DETECT_BYTES)
        return cpg_bytes, dbf_bytes

    path = Path(file_path)
    if path.suffix.lower() != ".shp":
        return None

    cpg_path = path.with_suffix(".cpg")
    dbf_path = path.with_suffix(".dbf")
    cpg_bytes = cpg_path.read_bytes() if cpg_path.exists() else None
    dbf_bytes = None
    if dbf_path.exists():
        with open(dbf_path, "rb") as handle:
            dbf_bytes = handle.read(_ENCODING_DETECT_BYTES)
    return cpg_bytes, dbf_bytes


def _resolve_zip_source(file_path: str) -> str:
    """Return the GDAL source path for a ZIP archive.

    GDAL cannot open a ``.zip`` by plain path — ``ogr.Open("x.zip")`` fails with
    "not recognized as being in a supported file format". The archive must be
    addressed through the ``/vsizip/`` virtual filesystem, and when the dataset
    sits in a subdirectory that subdirectory has to be part of the path
    (``/vsizip/x.zip/data``); ``/vsizip/x.zip`` alone fails just the same.

    Only single-dataset archives are supported: ``ogr2ogr ... -nln <table>``
    writes every layer it finds into that one table, so each layer would
    silently overwrite the previous one (``-overwrite``) and only the last
    would survive. Raise instead of losing data.

    Non-ZIP paths are returned unchanged.
    """
    if not zipfile.is_zipfile(file_path):
        return file_path

    with zipfile.ZipFile(file_path) as archive:
        names = [name for name in archive.namelist() if not name.endswith("/")]

    # A shapefile is a set of sidecar files sharing one basename; every other
    # supported format is a single file. Group by directory + stem so a
    # shapefile counts once rather than once per extension.
    datasets: dict[tuple[str, str], None] = {}
    for name in names:
        path = Path(name)
        if path.suffix.lower() in _SHAPEFILE_SIDECAR_SUFFIXES:
            continue
        datasets[(str(path.parent), path.stem)] = None

    if not datasets:
        raise Exception(f"No geospatial dataset found in archive {Path(file_path).name}")

    if len(datasets) > 1:
        found = ", ".join(sorted(stem for _, stem in datasets))
        raise Exception(
            f"Archive {Path(file_path).name} contains multiple datasets ({found}). "
            "Only single-dataset archives are supported: extract the one to import "
            "and upload it on its own."
        )

    (parent, _stem) = next(iter(datasets))
    source = f"/vsizip/{file_path}"
    # "." is what Path(...).parent yields for a member at the archive root.
    if parent not in (".", ""):
        source = f"{source}/{parent}"
    return source


def ingest_file_with_ogr2ogr(
    file_path: str,
    table_name: str,
    engine: Engine,
    schema: str = DEFAULT_SCHEMA,
) -> None:
    """Ingest a geospatial file into a PostGIS table using ogr2ogr.

    ZIP archives are addressed through GDAL's ``/vsizip/`` virtual filesystem
    (see :func:`_resolve_zip_source`).

    Args:
        file_path: Path to the local file to ingest
        table_name: Target table name in PostGIS
        engine: SQLAlchemy engine for the target PostGIS database
        schema: Target schema (default: public)
    """
    validate_table_name(table_name, max_length=POSTGIS_TABLE_NAME_MAX_LENGTH)
    validate_schema_name(schema)

    # Detect before rewriting the path: the helper reads the archive itself.
    shape_encoding = _detect_shapefile_encoding(file_path)
    file_path = _resolve_zip_source(file_path)

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
        "-forceNullable",
        # Single geometries (e.g. a shapefile of simple Polygons) are promoted to
        # their Multi* equivalent so a later chunk/feature that happens to be a
        # Multi* geometry doesn't clash with the column type PostGIS inferred
        # from the first rows.
        "-nlt",
        "PROMOTE_TO_MULTI",
        "-lco",
        f"GEOMETRY_NAME={DEFAULT_GEOMETRY_COLUMN}",
        "-lco",
        f"SCHEMA={schema}",
    ]

    # Only set when the shapefile has no .cpg and is not UTF-8; otherwise GDAL's
    # own handling (.cpg, or UTF-8 by default) is already correct.
    if shape_encoding is not None:
        command += ["--config", "SHAPE_ENCODING", shape_encoding]

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
            # Use requests for HTTP/HTTPS URLs. The response is streamed straight to
            # disk: ogr2ogr needs a real file anyway, and buffering the whole body in
            # memory first would defeat the point of handing the file to GDAL.
            resolved_url = resolve_url(url)
            with requests.get(resolved_url, auth=auth, timeout=300, stream=True) as response:
                response.raise_for_status()

                # Headers are available before the body is consumed.
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
                        for chunk in response.iter_content(chunk_size=_DOWNLOAD_CHUNK_SIZE):
                            temp_file.write(chunk)

                    ingest_file_with_ogr2ogr(str(temp_file_path), table_name, engine, schema)

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
        "-forceNullable",
        "-nlt",
        "PROMOTE_TO_MULTI",
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
_WFS_JSON_FORMATS = ("application/json", "application/geo+json", "json", "geojson")


def _normalize_oapif_url(url: str) -> str:
    """Strip /collections[/...] suffixes so GDAL's OAPIF driver receives the service root."""
    return _OAPIF_COLLECTIONS_RE.sub("", url.rstrip("/"))


def _wfs_json_output_format(service_url: str) -> str | None:
    """Return the first JSON-compatible outputFormat advertised by GetCapabilities, or None."""
    try:
        resp = requests.get(
            service_url,
            params={"SERVICE": "WFS", "REQUEST": "GetCapabilities"},
            timeout=30,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        advertised = {
            el.text.strip().lower()
            for el in root.iter()
            if (el.tag.split("}")[-1] if "}" in el.tag else el.tag) == "Value" and el.text
        }
        for fmt in _WFS_JSON_FORMATS:
            if fmt in advertised:
                return fmt
    except Exception as exc:
        logger.warning("Could not read WFS GetCapabilities from %s: %s", service_url, exc)
    return None


def _wfs_geojson_chunk_url(
    service_url: str,
    layer_name: str,
    offset: int,
    count: int,
    output_format: str = "application/json",
) -> str:
    """Build a WFS 2.0 GetFeature URL requesting JSON output with pagination.

    Bypasses the GML driver (and its curved-geometry issues) by requesting
    a JSON format directly from the server.
    """
    parsed = urlparse(service_url)
    params = {
        "SERVICE": "WFS",
        "VERSION": "2.0.0",
        "REQUEST": "GetFeature",
        "TYPENAMES": layer_name,
        "OUTPUTFORMAT": output_format,
        "startIndex": str(offset),
        "count": str(count),
    }
    return urlunparse(parsed._replace(query=urlencode(params)))


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
        "-forceNullable",
        "-lco",
        f"GEOMETRY_NAME={DEFAULT_GEOMETRY_COLUMN}",
        "-nlt",
        "PROMOTE_TO_MULTI",
        "-nlt",
        "CONVERT_TO_LINEAR",
        "-lco",
        f"SCHEMA={schema}",
    ]

    # OGC API - Features serves GeoJSON, which RFC 7946 pins to WGS84 lon/lat, so
    # stamping EPSG:4326 is safe and works around GDAL leaving SRID 0 (which would
    # break the downstream ST_Transform).
    #
    # A WFS is NOT covered by that guarantee: it serves whatever srsName was
    # negotiated, commonly a projected CRS such as EPSG:2154. Since -a_srs relabels
    # without reprojecting, forcing 4326 there would tag metric coordinates as
    # degrees and silently place the data far from where it belongs. Let GDAL keep
    # the SRS advertised by the service instead.
    if protocol == "ogcFeatures":
        command += ["-a_srs", DEFAULT_OGC_SRS]

    if auth is not None:
        username, password = auth
        # --------
        # WARNING: don't log the command — GDAL_HTTP_USERPWD contains credentials
        # --------
        command += ["--config", "GDAL_HTTP_USERPWD", f"{username}:{password}"]

    _run_ogr2ogr(command, context=f"ingesting OGC layer '{layer_name}' into {schema}.{table_name}")
