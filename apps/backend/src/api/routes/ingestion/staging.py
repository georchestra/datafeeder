import json
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import geopandas as gpd
import pandas as pd
import requests
from data_manipulation import (
    IntegrityTransformation,
    detect_column_type_from_sqla,
    read_and_transform_data,
)
from data_manipulation.constants import DB_URI_PREFIX
from data_manipulation.database import schema_exists, table_exists
from data_manipulation.ingestion import read_data_from_postgis
from data_manipulation.logging import configure_logging
from data_manipulation.models import ForceProjection as DataManipulationForceProjection
from data_manipulation.utils import sanitize_name
from data_manipulation.validators import validate_schema_name, validate_table_name
from fastapi import APIRouter, Body, File, Form, Header, HTTPException, Query, UploadFile
from shapely.geometry.base import BaseGeometry
from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.orm.attributes import flag_modified

from src.api.deps import DatafeederSessionDep, DataSessionDep, GeorchestraContextDep, OrgIdDep
from src.core.callback import build_callback_url
from src.core.config import get_staging_schema
from src.core.db import data_engine, source_db_key, source_engine
from src.core.encryption import encrypt_basic_auth
from src.core.logging import get_logger
from src.core.security import AccessLevel, load_authorized_integrity_link
from src.models import (
    StagingResponse,
)
from src.models.data_import import (
    ColumnConfig,
    FileType,
    ForceProjection,
    ImportType,
    StagingMetadata,
    StagingMetadataResponse,
    StagingPreviewResponse,
)
from src.models.integrity_link import IntegrityLink
from src.services.executor_factory import get_task_executor
from src.services.files import delete_temp_file, upload_file_to_temp

logger = get_logger()
configure_logging(logger)

router = APIRouter(prefix="/ingestion/staging", tags=["Ingestion"])


def _generate_staging_table_name() -> str:
    """Generate a unique, readable staging table name.

    Returns:
        A unique uuid staging table name
    """
    return sanitize_name(str(uuid4()))


def _remove_staging_table(staging_table_name: str) -> None:
    """Remove a staging table from the data database.

    Args:
        staging_table_name: The name of the staging table to remove

    Raises:
        Logs errors but does not raise exceptions
    """
    try:
        validate_table_name(staging_table_name, context="staging")

        schema = get_staging_schema()
        metadata = MetaData(schema=schema)
        table = Table(staging_table_name, metadata)
        table.drop(data_engine, checkfirst=True)

        logger.info(f"Successfully removed staging table: {staging_table_name}")
    except Exception as e:
        logger.error(f"Error removing staging table {staging_table_name}: {e}")


class _ImportSourceResult:
    def __init__(
        self,
        source: str,
        url: str,
        source_file_name: str | None,
        source_file_type: "FileType | None",
        auth_enabled: bool,
    ) -> None:
        self.source = source
        self.url = url
        self.source_file_name = source_file_name
        self.source_file_type = source_file_type
        self.auth_enabled = auth_enabled


async def _process_import_source(
    type: "ImportType",
    url: Optional[str] = None,
    file: Optional[UploadFile] = None,
    auth_enabled: bool = False,
    username: Optional[str] = None,
    password: Optional[str] = None,
    ftp_host: Optional[str] = None,
    ftp_port: Optional[int] = None,
    ftp_path: Optional[str] = None,
    db_schema: Optional[str] = None,
    db_table: Optional[str] = None,
) -> _ImportSourceResult:
    """Process the import source and extract file metadata.

    Returns:
        _ImportSourceResult containing source, url, source_file_name, source_file_type, auth_enabled
    """
    source = None
    source_file_name = None
    source_file_type = None

    match type:
        case ImportType.FILE:
            if file is None:
                raise HTTPException(status_code=400, detail="File is required")

            source_file_name, source_file_type, file_url = await upload_file_to_temp(
                file, rand_id=str(uuid4())
            )
            source = file_url
            url = file_url

        case ImportType.URL:
            if not url:
                logger.error("URL is required for URL import type")
                raise HTTPException(status_code=400, detail="URL is required for URL import type")

            source = url
            source_file_name, source_file_type = _extract_url_metadata(
                url, auth_enabled, username, password
            )

        case ImportType.FTP:
            ftp_host = ftp_host.strip() if ftp_host else None
            ftp_path = ftp_path.strip() if ftp_path else None

            if not ftp_host or not ftp_port or not ftp_path or not username or not password:
                logger.error(
                    "FTP host, port, path, username and password are required for FTP import type"
                )
                raise HTTPException(
                    status_code=400,
                    detail="FTP host, port, path, username and password are required for FTP import type",
                )

            source = f"ftp://{ftp_host}:{ftp_port}/{ftp_path}"
            url = source
            source_file_name = ftp_path.rsplit("/", 1)[-1]
            source_file_type = _extract_filetype(source_file_name)
            auth_enabled = True

        case ImportType.DATABASE:
            if not db_schema or not db_table:
                raise HTTPException(
                    status_code=400,
                    detail="Schema and table are required for database import type",
                )
            try:
                validate_schema_name(db_schema)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))

            try:
                validate_table_name(db_table)
            except ValueError as e:
                raise HTTPException(status_code=422, detail=str(e))

            if not source_engine or not source_db_key:
                raise HTTPException(status_code=503, detail="No source database configured")

            if not schema_exists(source_engine, db_schema):
                raise HTTPException(
                    status_code=422,
                    detail=f"Schema '{db_schema}' not found in source database",
                )
            if not table_exists(source_engine, db_schema, db_table):
                raise HTTPException(
                    status_code=422,
                    detail=f"Table '{db_table}' not found in schema '{db_schema}'",
                )

            source = f"{DB_URI_PREFIX}{source_db_key}/{db_schema}/{db_table}"
            url = source
            auth_enabled = False

        case ImportType.API:
            logger.error(f"Import type {type.value} not implemented yet")
            raise HTTPException(
                status_code=501, detail=f"Import type {type.value} not implemented yet"
            )

    return _ImportSourceResult(
        source=source,
        url=url,
        source_file_name=source_file_name,
        source_file_type=source_file_type,
        auth_enabled=auth_enabled,
    )


def _trigger_staging_task(
    integrity_link: "IntegrityLink",
    staging_table_name: str,
    source: str,
    import_type: "ImportType",
    encrypted_password: Optional[str],
    dag_run_id: str,
) -> "StagingResponse":
    """Trigger the Airflow staging DAG and return the response.

    Returns:
        StagingResponse with integrity link ID, DAG ID, DAG run ID, and current status
    """
    callback_params = {"integrity_link_id": str(integrity_link.id)}
    success_callback_url = build_callback_url("/ingestion/staging/dag_success", callback_params)
    failure_callback_url = build_callback_url("/ingestion/staging/dag_failure", callback_params)

    logger.info(f"Success callback URL: {success_callback_url}")
    logger.info(f"Failure callback URL: {failure_callback_url}")
    logger.info(
        f"Triggering staging_dag with source_type: {import_type.value.upper()} and source: {source}"
    )

    try:
        executor = get_task_executor()
        task_info = executor.trigger_staging_task(
            run_id=dag_run_id,
            staging_table_name=staging_table_name,
            source=str(source),
            source_type=import_type.value.upper(),
            success_callback_url=success_callback_url,
            failure_callback_url=failure_callback_url,
            encrypted_credentials=encrypted_password,
        )

        return StagingResponse(
            integrity_link_id=str(integrity_link.id),
            dag_id=task_info.task_id,
            dag_run_id=task_info.run_id,
            status=task_info.status,
        )
    except Exception as e:
        logger.error(f"Error triggering task: {e}")
        raise HTTPException(status_code=500, detail=f"Task execution error: {e}")


def _extract_filetype(filename: str) -> FileType | None:
    """Extract file type from filename extension.

    Args:
        filename: The filename or path to extract the type from

    Returns:
        The FileType enum value or None if extension is not recognized
    """
    if not filename:
        return None

    # Extract extension and convert to lowercase
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Map extensions to FileType
    extension_map = {
        "csv": FileType.CSV,
        "geojson": FileType.GEOJSON,
        "json": FileType.JSON,
        "shp": FileType.SHAPEFILE,
        "gpkg": FileType.GPKG,
        "zip": FileType.ZIP,
    }

    return extension_map.get(extension)


def _extract_url_metadata(
    url: str, auth_enabled: bool = False, username: str | None = None, password: str | None = None
) -> tuple[str | None, FileType | None]:
    """Extract file name and file type from a URL using HEAD request.

    Args:
        url: The URL to inspect
        auth_enabled: Whether to use Basic Auth for the request
        username: Basic Auth username (if auth_enabled is True)
        password: Basic Auth password (if auth_enabled is True)

    Returns:
        A tuple of (source_file_name, source_file_type)

    Raises:
        HTTPException: If the URL cannot be accessed or has unsupported content type
    """
    try:
        headers = {
            "Accept": "*/*",
        }
        head_response = requests.head(
            url,
            headers=headers,
            allow_redirects=True,
            auth=(username, password) if auth_enabled and username and password else None,
        )
        head_response.raise_for_status()

        source_file_name = None
        content_disposition = head_response.headers.get("content-disposition")
        if content_disposition:
            fname = re.findall("filename=(.+)", content_disposition)
            if not fname:
                fname = re.findall("filename\\*=UTF-8''(.+)", content_disposition)

            if not fname:
                logger.warning(f"Filename not found in content-disposition for URL {url}")
            # If filename is found, strip quotes and extract base name without extension
            else:
                source_file_name = fname[0].strip('"').rsplit(".", 1)[0]

        source_file_type = None
        content_type = head_response.headers.get("content-type")
        if content_type:
            # Extract the MIME type without parameters (e.g., charset)
            mime_type = content_type.split(";")[0].strip().lower()
            if mime_type in (
                "application/vnd.geo+json",
                "application/geo+json",
                "application/json",
            ):
                source_file_type = FileType.GEOJSON
            elif mime_type in ("text/csv", "application/csv"):
                source_file_type = FileType.CSV
            elif mime_type in ("application/geopackage+sqlite3", "application/x-sqlite3"):
                source_file_type = FileType.GPKG
            elif "application/zip" in content_type:
                # TODO: could be shapefile or zipped CSV, need better detection
                source_file_type = FileType.SHAPEFILE
            else:
                logger.warning(f"Un-detected content type from URL {url}: {mime_type}")

        return source_file_name, source_file_type

    except Exception as e:
        logger.error(f"Error accessing URL {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Error accessing URL: {e}")


@router.post(
    "/",
    response_model=StagingResponse,
    summary="Submit data for staging import",
    description="Submit data for staging import by triggering the Airflow staging DAG.",
)
async def submit_staging(
    session: DatafeederSessionDep,
    type: ImportType = Form(...),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    auth_enabled: bool = Form(False),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    ftp_host: Optional[str] = Form(None),
    ftp_port: Optional[int] = Form(None),
    ftp_path: Optional[str] = Form(None),
    db_schema: Optional[str] = Form(None),
    db_table: Optional[str] = Form(None),
    sec_username: str = Header(..., alias="sec-username", include_in_schema=False),
    sec_org: str = Header(..., alias="sec-org", include_in_schema=False),
) -> StagingResponse:
    """
    Submit data for staging import.

    Args:
        type: Import type (file, URL, FTP, database, etc.)
        url: Optional URL if import type is URL
        file: Optional file upload if import type is file
        auth_enabled: Whether authentication is enabled for the source
        username: Optional username for authentication
        password: Optional password for authentication
        ftp_host: Optional FTP host if import type is FTP
        ftp_port: Optional FTP port if import type is FTP
        ftp_path: Optional FTP path if import type is FTP
        db_schema: Optional schema name if import type is database
        db_table: Optional table name if import type is database
        sec_username: Username from geOrchestra security headers
        sec_org: Organization from geOrchestra security headers

    Returns:
        StagingResponse with integrity link ID, DAG ID, DAG run ID, and current DAG run status
    """
    url = url.strip() if url else None
    username = username.strip() if username else None
    password = password.strip() if password else None

    import_source = await _process_import_source(
        type=type,
        url=url,
        file=file,
        auth_enabled=auth_enabled,
        username=username,
        password=password,
        ftp_host=ftp_host,
        ftp_port=ftp_port,
        ftp_path=ftp_path,
        db_schema=db_schema.strip() if db_schema else None,
        db_table=db_table.strip() if db_table else None,
    )

    staging_table_name = _generate_staging_table_name()

    encrypted_password = None
    if import_source.auth_enabled and username and password:
        try:
            encrypted_password = encrypt_basic_auth(session.connection(), username, password)
        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise HTTPException(status_code=500, detail="Failed to encrypt credentials")

    integrity_link = IntegrityLink(
        integrity_owner=sec_username,
        integrity_organization=sec_org,
        source_import_type=type,
        source_url=import_source.url,
        source_file_name=import_source.source_file_name,
        source_file_type=import_source.source_file_type,
        source_username=username if import_source.auth_enabled else None,
        source_password_encrypted=encrypted_password if import_source.auth_enabled else None,
        staging_table_name=staging_table_name,
    )
    session.add(integrity_link)
    session.commit()
    session.refresh(integrity_link)

    integrity_link_id_as_string = str(integrity_link.id)

    logger.info(
        f"Created IntegrityLink {integrity_link.id} for DAG run {integrity_link_id_as_string} | "
        f"owner={sec_username} | org={sec_org} | table={staging_table_name}"
    )

    return _trigger_staging_task(
        integrity_link=integrity_link,
        staging_table_name=staging_table_name,
        source=import_source.source,
        import_type=type,
        encrypted_password=encrypted_password,
        dag_run_id=integrity_link_id_as_string,
    )


@router.put(
    "/{integrity_link_id}",
    response_model=StagingResponse,
    summary="Submit data for existing staging import",
    description="Submit data for existing staging import by triggering the Airflow staging DAG.",
)
async def edit_staging(
    session: DatafeederSessionDep,
    integrity_link_id: str,
    type: ImportType = Form(...),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    auth_enabled: bool = Form(False),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    ftp_host: Optional[str] = Form(None),
    ftp_port: Optional[int] = Form(None),
    ftp_path: Optional[str] = Form(None),
    db_schema: Optional[str] = Form(None),
    db_table: Optional[str] = Form(None),
    sec_username: str = Header(..., alias="sec-username", include_in_schema=False),
    sec_org: str = Header(..., alias="sec-org", include_in_schema=False),
) -> StagingResponse:
    """
    Submit data for existing staging import.

    Args:
        integrity_link_id: IntegrityLink UUID to update
        type: Import type (file, URL, FTP, database, etc.)
        url: Optional URL if import type is URL
        file: Optional file upload if import type is file
        auth_enabled: Whether authentication is enabled for the source
        username: Optional username for authentication
        password: Optional password for authentication
        ftp_host: Optional FTP host if import type is FTP
        ftp_port: Optional FTP port if import type is FTP
        ftp_path: Optional FTP path if import type is FTP
        db_schema: Optional schema name if import type is database
        db_table: Optional table name if import type is database
        sec_username: Username from geOrchestra security headers
        sec_org: Organization from geOrchestra security headers

    Returns:
        StagingResponse with integrity link ID, DAG ID, DAG run ID, and current DAG run status
    """
    url = url.strip() if url else None
    username = username.strip() if username else None
    password = password.strip() if password else None

    import_source = await _process_import_source(
        type=type,
        url=url,
        file=file,
        auth_enabled=auth_enabled,
        username=username,
        password=password,
        ftp_host=ftp_host,
        ftp_port=ftp_port,
        ftp_path=ftp_path,
        db_schema=db_schema.strip() if db_schema else None,
        db_table=db_table.strip() if db_table else None,
    )

    staging_table_name = _generate_staging_table_name()

    encrypted_password = None
    if import_source.auth_enabled and username and password:
        try:
            encrypted_password = encrypt_basic_auth(session.connection(), username, password)
        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise HTTPException(status_code=500, detail="Failed to encrypt credentials")

    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    old_staging_table_name = integrity_link.staging_table_name

    integrity_link.source_import_type = type
    integrity_link.source_url = import_source.url
    integrity_link.source_file_name = import_source.source_file_name
    integrity_link.source_file_type = import_source.source_file_type
    integrity_link.source_username = username if import_source.auth_enabled else None
    integrity_link.source_password_encrypted = (
        encrypted_password if import_source.auth_enabled else None
    )
    integrity_link.staging_table_name = staging_table_name
    integrity_link.integrity_transformation = None  # Clear any existing transformations on edit !! warning this may break process if recurrent edits are needed, need to find better way to handle this

    session.commit()
    session.refresh(integrity_link)

    _remove_staging_table(old_staging_table_name)

    dag_run_id = f"{integrity_link.id}_{int(datetime.now(timezone.utc).timestamp())}"

    logger.info(
        f"Updated IntegrityLink {integrity_link.id} | "
        f"owner={integrity_link.integrity_owner} | org={integrity_link.integrity_organization} | table={staging_table_name}"
    )

    return _trigger_staging_task(
        integrity_link=integrity_link,
        staging_table_name=staging_table_name,
        source=import_source.source,
        import_type=type,
        encrypted_password=encrypted_password,
        dag_run_id=dag_run_id,
    )


@router.post("/dag_success")
def dag_success_callback(
    session: DatafeederSessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
) -> None:
    """
    Success callback endpoint called by Airflow DAG on successful completion.
    Updates the existing IntegrityLink record with job duration.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
    """
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    if integrity_link.created_at is None:
        raise HTTPException(status_code=500, detail="IntegrityLink created_at is missing")

    now = datetime.now(timezone.utc)
    created_at = (
        integrity_link.created_at.replace(tzinfo=timezone.utc)
        if integrity_link.created_at.tzinfo is None
        else integrity_link.created_at
    )
    integrity_link.staging_retrieve_time = now - created_at
    session.commit()
    session.refresh(integrity_link)

    try:
        # db:// URIs reference a remote table, not a filesystem path — skip deletion for DATABASE
        if integrity_link.source_url and integrity_link.source_import_type != ImportType.DATABASE:
            delete_temp_file(integrity_link.source_url)
    except Exception as e:
        logger.error(f"Error deleting temp file: {e}")


@router.post("/dag_failure")
def dag_failure_callback(
    datafeeder_session: DatafeederSessionDep,
    data_session: DataSessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    reason: str | None = Query(None, description="Failure reason"),
) -> None:
    """
    Failure callback endpoint called by Airflow DAG on failure.
    Deletes the IntegrityLink and drops the staging table.

    Args:
        datafeeder_session: Datafeeder database session (injected)
        data_session: Data database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
    """
    integrity_link = datafeeder_session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    if integrity_link.staging_table_name:
        try:
            validate_table_name(integrity_link.staging_table_name, context="staging")
            schema = get_staging_schema()
            table = Table(integrity_link.staging_table_name, MetaData(schema=schema))
            table.drop(data_engine, checkfirst=True)
            data_session.commit()
        except ValueError as e:
            logger.error(f"Invalid staging table name in database: {e}")
        except Exception as e:
            logger.error(f"Error dropping staging table {integrity_link.staging_table_name}: {e}")

    datafeeder_session.delete(integrity_link)
    datafeeder_session.commit()


def _detect_original_projection(
    staging_table_name: str,
    engine: Any,
    schema: str | None,
) -> str | None:
    """Return the CRS string if the staging table contains geographic data."""
    try:
        sample = read_data_from_postgis(staging_table_name, engine, schema, limit=1)
        if isinstance(sample, gpd.GeoDataFrame) and sample.crs is not None:
            return sample.crs.to_string()
    except Exception as e:
        logger.warning(f"Could not detect original projection: {e}")
    return None


def _resolve_columns(
    saved_transformation: dict[str, Any] | None,
    table: Table,
) -> tuple[list[ColumnConfig], dict[str, Any] | None]:
    """Return (columns, force_projection_data) from saved config or live DB schema."""
    column_sqla_types = {col.name: col.type for col in table.columns}

    if saved_transformation:
        raw_columns = saved_transformation.get("columns")
        if raw_columns:
            try:
                columns: list[ColumnConfig] = []
                for raw_col in raw_columns:
                    col_cfg = ColumnConfig.model_validate(raw_col)
                    sqla_type = column_sqla_types.get(col_cfg.original_name)
                    if sqla_type is not None:
                        col_cfg = col_cfg.model_copy(
                            update={"original_type": detect_column_type_from_sqla(sqla_type)}
                        )
                    columns.append(col_cfg)
                return columns, saved_transformation.get("force_projection")
            except Exception as e:
                logger.warning(f"Could not deserialize saved columns config: {e}")

    columns = [
        ColumnConfig(
            original_name=col.name,
            original_type=detect_column_type_from_sqla(col.type),
        )
        for col in table.columns
    ]
    return columns, None


@router.get("/{integrity_link_id}/metadata")
def get_staging_metadata(
    data_session: DataSessionDep,
    datafeeder_session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: str,
    org_id: OrgIdDep,
) -> StagingMetadataResponse:
    """
    Get metadata of the staging table.

    If a transformation configuration has been saved via PUT metadata, the saved
    column configurations (with rename/exclude/cast/filter settings) are returned.
    Otherwise, columns are built from the staging table schema (original names only).

    Args:
        data_session: Data database session (injected)
        datafeeder_session: Datafeeder database session (injected)
        geo_ctx: geOrchestra security context
        integrity_link_id: IntegrityLink UUID (required)

    Returns:
        Metadata of the staging table
    """
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.METADATA_WRITE, geo_ctx, datafeeder_session, org_id
    )

    staging_table_name = integrity_link.staging_table_name
    source_import_type = integrity_link.source_import_type
    source_file_type = integrity_link.source_file_type
    title = integrity_link.integrity_title or integrity_link.source_file_name or ""
    if (
        not title
        and integrity_link.source_import_type == ImportType.DATABASE
        and integrity_link.source_url
    ):
        # source_url format: db://{db_key}/{schema}/{table} — take the last segment
        title = integrity_link.source_url.rsplit("/", 1)[-1]
    force_projection_data = (
        integrity_link.integrity_transformation.get("force_projection")
        if integrity_link.integrity_transformation
        else None
    )

    schema = get_staging_schema()
    table = Table(
        staging_table_name,
        MetaData(schema=schema),
        autoload_with=data_engine,
    )
    row_count = data_session.scalar(select(func.count()).select_from(table)) or 0
    original_projection = _detect_original_projection(
        staging_table_name,
        data_engine,
        schema,
    )
    columns, force_projection_data = _resolve_columns(
        integrity_link.integrity_transformation, table
    )

    return StagingMetadataResponse(
        title=title,
        import_type=source_import_type,
        file_type=source_file_type,
        columns=columns,
        row_count=row_count,
        force_projection=ForceProjection.model_validate(force_projection_data)
        if force_projection_data
        else None,
        original_projection=original_projection,
        has_final_table=integrity_link.final_table_name is not None,
    )


@router.put("/{integrity_link_id}/metadata")
def edit_staging_metadata(
    data_session: DataSessionDep,
    datafeeder_session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: str,
    org_id: OrgIdDep,
    config: StagingMetadata = Body(
        ...,
        description="Staging configuration including columns, file type, projection, and title",
    ),
) -> StagingMetadataResponse:
    """
    Configure staging data endpoint called by frontend to update IntegrityLink
    with any additional configuration before finalizing the import.

    Validates column names (empty or duplicate new_name values are rejected).
    Persists the full IntegrityTransformation (columns + force_projection) to the DB.

    Args:
        data_session: Data database session (injected)
        datafeeder_session: Datafeeder database session (injected)
        geo_ctx: geOrchestra security context
        integrity_link_id: IntegrityLink UUID (required)
        config: Staging configuration with columns (ColumnConfig list), file_type,
                force_projection, and title

    Returns:
        Updated staging metadata with saved column configurations
    """
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.METADATA_WRITE, geo_ctx, datafeeder_session, org_id
    )

    if config.columns:
        # Validate column names: no empty names and no duplicates (after rename).
        # `name` is the *effective* output name for each column: new_name if set,
        # original_name otherwise.  Checking effective names catches all collision
        # scenarios including new_name of one column clashing with original_name of
        # another (when that column has no new_name).
        seen: set[str] = set()
        for col in config.columns:
            name = col.new_name or col.original_name
            if not name or not name.strip():
                raise HTTPException(
                    status_code=422,
                    detail=f"Column '{col.original_name}' has an empty name. "
                    "Column names cannot be empty.",
                )
            if name in seen:
                raise HTTPException(
                    status_code=422,
                    detail=f"Duplicate column name '{name}'. Each column must have a unique name.",
                )
            seen.add(name)

    if config.title:
        integrity_link.source_file_name = config.title
    if config.file_type:
        integrity_link.source_file_type = config.file_type

    force_proj = (
        DataManipulationForceProjection(
            type=config.force_projection.type,
            x_column=config.force_projection.x_column,
            y_column=config.force_projection.y_column,
        )
        if config.force_projection
        else None
    )
    transformation = IntegrityTransformation(
        columns=config.columns or None,
        force_projection=force_proj,
    )
    integrity_link.integrity_transformation = transformation.model_dump(mode="json")
    flag_modified(integrity_link, "integrity_transformation")

    datafeeder_session.commit()
    datafeeder_session.refresh(integrity_link)

    return get_staging_metadata(
        data_session=data_session,
        datafeeder_session=datafeeder_session,
        geo_ctx=geo_ctx,
        integrity_link_id=integrity_link_id,
        org_id=org_id,
    )


@router.get("/{integrity_link_id}/preview")
def get_staging_preview(
    data_session: DataSessionDep,
    datafeeder_session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: str,
    org_id: OrgIdDep,
    limit: int = Query(10, description="Number of rows to preview"),
    raw: bool = Query(
        False,
        description=(
            "When true, return original data ignoring saved transformation config. "
            "Used as fallback when transformation causes an error."
        ),
    ),
    include_excluded: bool = Query(
        False,
        description=(
            "When true, return all columns including those flagged as excluded "
            "in the transformation config. Other transformations (rename, cast, "
            "filter, projection) are still applied."
        ),
    ),
) -> StagingPreviewResponse:
    """
    Get a preview of the data in the staging table.

    Returns both tabular data (for table display) and GeoJSON (for map display).

    When raw=false (default): applies saved transformation config (exclusion, filters,
    rename, cast, projection). When raw=true: returns original data without any
    transformation applied (useful as fallback on preview error).

    When include_excluded=true: returns all columns including those flagged as
    excluded, while still applying other transformations (rename, cast, filter,
    projection).

    Args:
        data_session: Data database session (injected)
        datafeeder_session: Datafeeder database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        limit: Number of rows to preview (optional, default is 10)
        raw: When true, bypass all transformations and return original data
        include_excluded: When true, return all columns even if flagged as excluded

    Returns:
        Preview data from the staging table, transformed based on saved config
    """

    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.METADATA_WRITE, geo_ctx, datafeeder_session, org_id
    )

    staging_table_name = integrity_link.staging_table_name
    if not staging_table_name:
        raise HTTPException(status_code=500, detail="Staging table name is missing")

    # Load transformation config from DB
    schema = get_staging_schema()
    engine = data_engine
    config: IntegrityTransformation | None = None

    if not raw and integrity_link.integrity_transformation:
        try:
            config = IntegrityTransformation.model_validate(integrity_link.integrity_transformation)
        except Exception as e:
            logger.warning(f"Could not deserialize transformation config, using raw: {e}")
    # SECURITY NOTE: when raw=True, config remains None and read_and_transform_data
    # returns ALL columns including those marked as excluded in the saved config.
    # This is intentional — raw mode is a debug/fallback path used when the
    # transformation itself causes a preview error. If excluded columns contain
    # sensitive data, access to this endpoint should be restricted at the
    # infrastructure level (authentication / authorisation) rather than relying
    # on the exclusion flag alone.

    # Track whether the geom column is explicitly excluded in the saved config.
    # Used below to suppress map data even when include_excluded=True.
    geom_excluded_in_config = (
        not raw
        and config is not None
        and config.columns is not None
        and any(col.original_name == "geom" and col.excluded for col in config.columns)
    )

    # When include_excluded is requested, strip excluded=True from all columns
    # so SQL-level filtering keeps them in the query results.
    if include_excluded and config is not None and config.columns:
        config = config.model_copy(
            update={
                "columns": [
                    ColumnConfig(
                        original_name=col.original_name,
                        original_type=col.original_type,
                        new_name=col.new_name,  # renaming should still apply to excluded columns in preview
                        excluded=False,  # override to False to include in preview
                        cast_type=None,  # cast is not supported in preview, so ignore any cast_type in config
                        filter=None,  # filter is not supported in preview, so ignore any filter_expression in config
                    )
                    if col.excluded
                    else col
                    for col in config.columns
                ]
            }
        )

    try:
        transformed_data = read_and_transform_data(
            staging_table_name, engine, schema, config, limit=limit
        )

        # Convert all non-JSON-serializable types to string (datetime, Timestamp, etc.)
        for col in transformed_data.columns:
            if transformed_data[col].dtype == "object":
                try:
                    if pd.api.types.is_datetime64_any_dtype(transformed_data[col]):
                        transformed_data[col] = transformed_data[col].astype(str)  # type: ignore[misc]
                except Exception:
                    pass
            elif pd.api.types.is_datetime64_any_dtype(transformed_data[col]):
                transformed_data[col] = transformed_data[col].astype(str)  # type: ignore[misc]

        data: list[dict[str, Any]] = []
        geojson_data = None
        is_geographic = False

        # Convert geometry to WKT for tabular display if GeoDataFrame
        if isinstance(transformed_data, gpd.GeoDataFrame):
            is_geographic = True

            geometry_cols: list[str] = []
            for col in transformed_data.columns:  # type: ignore[misc]
                if not transformed_data[col].empty:  # type: ignore[misc]
                    sample_item = transformed_data[col].iloc[0]
                    sample: Any = sample_item  # type: ignore[misc]

                    if isinstance(sample, BaseGeometry):
                        geometry_cols.append(col)  # type: ignore[misc]
                    elif hasattr(sample_item, "wkt"):  # type: ignore[misc]
                        geometry_cols.append(col)  # type: ignore[misc]

            logger.info(f"Found geometry columns: {geometry_cols}")

            # Create GeoJSON for map display first, force to EPSG:4326
            map_gdf = transformed_data.copy()

            try:
                if map_gdf.crs and map_gdf.crs.to_string() != "EPSG:4326":
                    map_gdf = map_gdf.to_crs("EPSG:4326")
                    logger.info(f"Reprojected data from {map_gdf.crs} to EPSG:4326 for map display")
            except Exception as crs_error:
                logger.warning(f"Could not reproject to EPSG:4326: {crs_error}")

            # Modify transformed_data directly for tabular display
            if "geom" in geometry_cols:
                transformed_data["geom"] = transformed_data["geom"].apply(  # type: ignore[misc]
                    lambda geom: geom.wkt if geom is not None else None  # type: ignore[misc]
                )
                geometry_cols.remove("geom")

            # Drop extra geometry columns for tabular data
            table_data = transformed_data.drop(columns=geometry_cols, errors="ignore")
            data = table_data.to_dict(orient="records")  # type: ignore[misc]

            geojson_str = map_gdf.to_json()  # type: ignore[misc]
            geojson_data = json.loads(geojson_str) if geojson_str else None
        else:
            # Regular DataFrame, no geometry conversion needed
            data = transformed_data.to_dict(orient="records")  # type: ignore[misc]

        # If the geom column was excluded in the saved config, suppress map data
        # regardless of include_excluded. Raw mode bypasses this rule.
        if geom_excluded_in_config:
            is_geographic = False
            geojson_data = None

        return StagingPreviewResponse(
            data=data,  # type: ignore[misc]
            geojson=geojson_data,
            is_geographic=is_geographic,
        )

    except Exception as e:
        logger.error(f"Error applying transformations for preview: {e}")
        raise HTTPException(status_code=500, detail=f"{e}")
