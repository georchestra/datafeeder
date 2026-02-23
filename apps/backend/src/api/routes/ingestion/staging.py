import json
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import geopandas as gpd
import pandas as pd
import requests
from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from data_manipulation import IntegrityTransformation, read_and_transform_data
from data_manipulation.ingestion import read_data_from_postgis
from data_manipulation.logging import configure_logging
from data_manipulation.models import ForceProjection as DataManipulationForceProjection
from data_manipulation.utils import sanitize_name
from fastapi import APIRouter, Body, File, Form, Header, HTTPException, Query, UploadFile
from shapely.geometry.base import BaseGeometry
from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.orm.attributes import flag_modified

from src.api.deps import DatakernSessionDep, DataSessionDep
from src.core.callback import build_callback_url
from src.core.config import get_staging_schema
from src.core.db import data_engine
from src.core.encryption import encrypt_basic_auth
from src.core.logging import get_logger
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
from src.services.airflow_client import get_dag_run_api
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
    session: DatakernSessionDep,
    type: ImportType = Form(...),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    auth_enabled: bool = Form(False),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    ftp_host: Optional[str] = Form(None),
    ftp_port: Optional[int] = Form(None),
    ftp_path: Optional[str] = Form(None),
    sec_username: str = Header(..., alias="sec-username", include_in_schema=False),
    sec_org: str = Header(..., alias="sec-org", include_in_schema=False),
) -> StagingResponse:
    """
    Submit data for staging import.

    Args:
        request: Import configuration including type and optional URL
        sec_username: Username from geOrchestra security headers
        sec_org: Organization from geOrchestra security headers

    Returns:
        StagingResponse with integrity link ID, DAG ID, DAG run ID, and current DAG run status
    """

    dag_run_id = str(uuid4())

    source = None
    source_file_name = None
    source_file_type = None

    url = url.strip() if url else None
    username = username.strip() if username else None
    password = password.strip() if password else None

    # Extract source, source_file_name, and source_file_type according to import type
    match type:
        case ImportType.FILE:
            if file is None:
                raise HTTPException(status_code=400, detail="File is required")

            source_file_name, source_file_type, file_url = await upload_file_to_temp(
                file, rand_id=dag_run_id
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

            # Construct FTP URL
            source = f"ftp://{ftp_host}:{ftp_port}/{ftp_path}"
            url = source
            source_file_name = ftp_path.rsplit("/", 1)[-1]
            source_file_type = _extract_filetype(source_file_name)

            # Force encrypted credentials for FTP since they are required
            auth_enabled = True

        case ImportType.DATABASE | ImportType.API:
            # TODO: implement handling for DATABASE and API import types
            logger.error(f"Import type {type.value} not implemented yet")
            raise HTTPException(
                status_code=501, detail=f"Import type {type.value} not implemented yet"
            )

    staging_table_name = _generate_staging_table_name()

    # Encrypt Basic Auth credentials if provided
    encrypted_password = None
    if auth_enabled and username and password:
        try:
            encrypted_password = encrypt_basic_auth(session.connection(), username, password)
        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise HTTPException(status_code=500, detail="Failed to encrypt credentials")

    # Create IntegrityLink immediately
    integrity_link = IntegrityLink(
        integrity_owner=sec_username,
        integrity_organization=sec_org,
        source_import_type=type,
        source_url=url,
        source_file_name=source_file_name,
        source_file_type=source_file_type,
        source_username=username if auth_enabled else None,
        source_password_encrypted=encrypted_password if auth_enabled else None,
        staging_table_name=staging_table_name,
    )
    session.add(integrity_link)
    session.commit()
    session.refresh(integrity_link)

    # Build callback parameters
    callback_params = {
        "integrity_link_id": str(integrity_link.id),
    }

    # Build callback URLs
    success_callback_url = build_callback_url("/ingestion/staging/dag_success", callback_params)
    failure_callback_url = build_callback_url("/ingestion/staging/dag_failure", callback_params)

    logger.info(
        f"Created IntegrityLink {integrity_link.id} for DAG run {dag_run_id} | "
        f"owner={sec_username} | org={sec_org} | table={staging_table_name}"
    )
    logger.info(f"Success callback URL: {success_callback_url}")
    logger.info(f"Failure callback URL: {failure_callback_url}")
    logger.info(
        f"Triggering staging_dag with source_type: {type.value.upper()} and source: {source}"
    )

    try:
        dag_run_response = get_dag_run_api().trigger_dag_run(
            dag_id="staging_dag",
            trigger_dag_run_post_body=TriggerDAGRunPostBody(
                dag_run_id=dag_run_id,
                conf={
                    "source": str(source),
                    "source_type": type.value.upper(),
                    "staging_table_name": staging_table_name,
                    "encrypted_credentials": encrypted_password if auth_enabled else None,
                    "success_callback_url": success_callback_url,
                    "failure_callback_url": failure_callback_url,
                },
            ),
        )

        return StagingResponse(
            integrity_link_id=str(integrity_link.id),
            dag_id=dag_run_response.dag_id,
            dag_run_id=dag_run_response.dag_run_id,
            status=dag_run_response.state,
        )
    except Exception as e:
        logger.error(f"Error triggering Airflow DAG: {e}")
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.post("/dag_success")
def dag_success_callback(
    session: DatakernSessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
) -> None:
    """
    Success callback endpoint called by Airflow DAG on successful completion.
    Updates the existing IntegrityLink record with job duration.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)

    Returns:
        Success message with updated IntegrityLink details
    """
    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Ensure created_at exists and is timezone-aware
    if integrity_link.created_at is None:
        raise HTTPException(
            status_code=500,
            detail="IntegrityLink created_at is missing",
        )

    # Calculate job duration
    now = datetime.now(timezone.utc)
    created_at = (
        integrity_link.created_at.replace(tzinfo=timezone.utc)
        if integrity_link.created_at.tzinfo is None
        else integrity_link.created_at
    )
    staging_retrieve_time = now - created_at

    # Update IntegrityLink
    integrity_link.staging_retrieve_time = staging_retrieve_time
    session.commit()
    session.refresh(integrity_link)

    # Remove file from temp folder if applicable
    try:
        if integrity_link.source_url:
            delete_temp_file(integrity_link.source_url)
    except Exception as e:
        logger.error(f"Error deleting temp file: {e}")


@router.post("/dag_failure")
def dag_failure_callback(
    datakern_session: DatakernSessionDep,
    data_session: DataSessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
) -> None:
    """
    Failure callback endpoint called by Airflow DAG on failure.
    Deletes the IntegrityLink and drops the staging table.

    Args:
        datakern_session: Datakern database session (injected)
        data_session: Data database session (injected)
        integrity_link_id: IntegrityLink UUID (required)

    Returns:
        Success message with cleanup details
    """
    # Query existing IntegrityLink
    integrity_link = datakern_session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Get staging table name
    staging_table_name = integrity_link.staging_table_name

    # Drop the staging table if it exists
    if staging_table_name:
        try:
            # CRITICAL: Validate table name before using in SQL (defense in depth)
            from data_manipulation.validators import validate_table_name

            validate_table_name(staging_table_name, context="staging")

            schema = get_staging_schema()
            metadata = MetaData(schema=schema)
            table = Table(staging_table_name, metadata)
            table.drop(data_session.get_bind(), checkfirst=True)
            data_session.commit()
        except ValueError as e:
            # Log validation error but continue with cleanup
            logger.error(f"Invalid staging table name in database: {e}")
        except Exception as e:
            # Log the error but continue with IntegrityLink deletion
            logger.error(f"Error dropping staging table {staging_table_name}: {e}")

    # Delete the IntegrityLink
    datakern_session.delete(integrity_link)
    datakern_session.commit()


@router.get("/{integrity_link_id}/metadata")
def get_staging_metadata(
    data_session: DataSessionDep,
    datakern_session: DatakernSessionDep,
    integrity_link_id: str,
) -> StagingMetadataResponse:
    """
    Get metadata of the staging table.

    If a transformation configuration has been saved via PUT metadata, the saved
    column configurations (with rename/exclude/cast/filter settings) are returned.
    Otherwise, columns are built from the staging table schema (original names only).

    Args:
        data_session: Data database session (injected)
        datakern_session: Datakern database session (injected)
        integrity_link_id: IntegrityLink UUID (required)

    Returns:
        Metadata of the staging table
    """

    integrity_link = datakern_session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    staging_table_name = integrity_link.staging_table_name
    source_import_type = integrity_link.source_import_type
    source_file_name = integrity_link.source_file_name
    source_file_type = integrity_link.source_file_type

    schema = get_staging_schema()
    sql_metadata = MetaData(schema=schema)
    table = Table(staging_table_name, sql_metadata, autoload_with=data_session.get_bind())

    row_count = data_session.scalar(select(func.count()).select_from(table)) or 0

    # Detect original projection if data is geographic
    original_projection = None
    try:
        sample_data = read_data_from_postgis(
            staging_table_name,
            data_session.get_bind(),  # type: ignore
            schema,
            limit=1,
        )
        if isinstance(sample_data, gpd.GeoDataFrame) and sample_data.crs is not None:
            original_projection = sample_data.crs.to_string()
    except Exception as e:
        logger.warning(f"Could not detect original projection: {e}")

    # Determine columns: use saved config if available, else build from DB schema
    saved_transformation = integrity_link.integrity_transformation
    saved_columns: list[ColumnConfig] | None = None
    force_projection_data: dict[str, Any] | None = None

    if saved_transformation:
        raw_columns = saved_transformation.get("columns")
        if raw_columns:
            try:
                saved_columns = [ColumnConfig.model_validate(c) for c in raw_columns]
            except Exception as e:
                logger.warning(f"Could not deserialize saved columns config: {e}")
        force_projection_data = saved_transformation.get("force_projection")

    if saved_columns is not None:
        columns = saved_columns
    else:
        # Build ColumnConfig from DB schema (no transformation configured yet)
        columns = [ColumnConfig(original_name=col.name) for col in table.columns]

    return StagingMetadataResponse(
        title=source_file_name or "",
        import_type=source_import_type,
        file_type=source_file_type,
        columns=columns,
        row_count=row_count,
        force_projection=ForceProjection.model_validate(force_projection_data)
        if force_projection_data
        else None,
        original_projection=original_projection,
    )


@router.put("/{integrity_link_id}/metadata")
def edit_staging_metadata(
    data_session: DataSessionDep,
    datakern_session: DatakernSessionDep,
    integrity_link_id: str,
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
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        config: Staging configuration with columns (ColumnConfig list), file_type,
                force_projection, and title

    Returns:
        Updated staging metadata with saved column configurations
    """
    # Query existing IntegrityLink
    integrity_link = datakern_session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Validate column names: reject empty new_name and duplicates
    if config.columns:
        effective_names: list[str] = []
        for col in config.columns:
            name = col.new_name if col.new_name is not None else col.original_name
            if not name or not name.strip():
                raise HTTPException(
                    status_code=422,
                    detail=f"Column '{col.original_name}' has an empty name. "
                    "Column names cannot be empty.",
                )
            effective_names.append(name)

        seen: set[str] = set()
        for name in effective_names:
            if name in seen:
                raise HTTPException(
                    status_code=422,
                    detail=f"Duplicate column name '{name}'. "
                    "Each column must have a unique name.",
                )
            seen.add(name)

    if config.title:
        integrity_link.source_file_name = config.title

    if config.file_type:
        integrity_link.source_file_type = config.file_type

    # Build and persist full IntegrityTransformation
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
        columns=config.columns if config.columns else None,
        force_projection=force_proj,
    )
    integrity_link.integrity_transformation = transformation.model_dump(mode="json")

    # Force SQLAlchemy to detect changes in the JSON column
    flag_modified(integrity_link, "integrity_transformation")

    datakern_session.commit()
    datakern_session.refresh(integrity_link)

    return get_staging_metadata(
        data_session=data_session,
        datakern_session=datakern_session,
        integrity_link_id=integrity_link_id,
    )


@router.get("/{integrity_link_id}/preview")
def get_staging_preview(
    data_session: DataSessionDep,
    datakern_session: DatakernSessionDep,
    integrity_link_id: str,
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
    ALL transformation configuration (columns AND force_projection) is loaded
    exclusively from the saved integrity_transformation — never from query params.

    When raw=false (default): applies saved transformation config (exclusion, filters,
    rename, cast, projection). When raw=true: returns original data without any
    transformation applied (useful as fallback on preview error).

    When include_excluded=true: returns all columns including those flagged as
    excluded, while still applying other transformations (rename, cast, filter,
    projection).

    Args:
        data_session: Data database session (injected)
        datakern_session: Datakern database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        limit: Number of rows to preview (optional, default is 10)
        raw: When true, bypass all transformations and return original data
        include_excluded: When true, return all columns even if flagged as excluded

    Returns:
        Preview data from the staging table, transformed based on saved config
    """

    integrity_link = datakern_session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    staging_table_name = integrity_link.staging_table_name
    if not staging_table_name:
        raise HTTPException(status_code=500, detail="Staging table name is missing")

    # Load transformation config from DB (ALL config comes from here, no query params)
    schema = get_staging_schema()
    engine = data_engine
    config: IntegrityTransformation | None = None

    if not raw and integrity_link.integrity_transformation:
        try:
            config = IntegrityTransformation.model_validate(
                integrity_link.integrity_transformation
            )
        except Exception as e:
            logger.warning(f"Could not deserialize transformation config, using raw: {e}")

    # When include_excluded is requested, strip excluded=True from all columns
    # so SQL-level filtering keeps them, while other transformations still apply.
    if include_excluded and config is not None and config.columns:
        config = config.model_copy(
            update={
                "columns": [
                    col.model_copy(update={"excluded": False}) if col.excluded else col
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
                    logger.info(
                        f"Reprojected data from {map_gdf.crs} to EPSG:4326 for map display"
                    )
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

        return StagingPreviewResponse(
            data=data,  # type: ignore[misc]
            geojson=geojson_data,
            is_geographic=is_geographic,
        )

    except Exception as e:
        logger.error(f"Error applying transformations for preview: {e}")
        raise HTTPException(status_code=500, detail=f"{e}")
