import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import requests
from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from data_manipulation.utils import sanitize_name
from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy import MetaData, Table, func, select

from src.api.deps import SessionDep
from src.core.callback import build_callback_url
from src.core.encryption import encrypt_basic_auth
from src.core.logging import get_logger
from src.models import (
    StagingResponse,
)
from src.models.data_import import (
    ColumnMetadata,
    FileType,
    ImportType,
    StagingMetadataResponse,
    StagingPreviewResponse,
)
from src.models.integrity_link import IntegrityLink
from src.services.airflow_client import get_dag_run_api
from src.services.files import delete_temp_file, upload_file_to_temp

router = APIRouter(prefix="/ingestion/staging", tags=["Ingestion"])
logger = get_logger()


def _generate_staging_table_name(dag_run_id: str, file_name: str | None) -> str:
    """Generate a unique, readable staging table name from an Airflow DAG run ID and optional file name.

    Args:
        dag_run_id: The Airflow DAG run ID
        file_name: The original file name (optional)

    Returns:
        A unique staging table name
    """

    MAX_TABLE_NAME_LENGTH = 63
    UUID_LENGTH = 36  # Length of UUID with hyphens
    SANITIZED_DAG_RUN_ID = sanitize_name(dag_run_id.replace("-", "_")[:UUID_LENGTH])

    if file_name:
        sanitized_name = sanitize_name(file_name.rsplit(".", 1)[0])[
            : MAX_TABLE_NAME_LENGTH - 1 - UUID_LENGTH
        ]
        return f"{sanitized_name}_{SANITIZED_DAG_RUN_ID}"

    return SANITIZED_DAG_RUN_ID


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
            elif mime_type == "text/csv":
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
    session: SessionDep,
    type: ImportType = Form(...),
    url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    auth_enabled: bool = Form(False),
    username: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
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

    # Extract source, source_file_name, and source_file_type according to import type
    match type:
        case ImportType.FILE:
            if file is None:
                raise HTTPException(status_code=400, detail="File is required")

            source_file_name, source_file_type, file_url = await upload_file_to_temp(
                file, rand_id=dag_run_id
            )
            source = url = file_url

        case ImportType.URL:
            if not url:
                logger.error("URL is required for URL import type")
                raise HTTPException(status_code=400, detail="URL is required for URL import type")

            source = url
            source_file_name, source_file_type = _extract_url_metadata(
                url, auth_enabled, username, password
            )

        case ImportType.DATABASE | ImportType.API:
            # TODO: implement handling for DATABASE and API import types
            logger.error(f"Import type {type.value} not implemented yet")
            raise HTTPException(
                status_code=501, detail=f"Import type {type.value} not implemented yet"
            )

    staging_table_name = _generate_staging_table_name(dag_run_id, source_file_name)

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
        source_auth_enabled=auth_enabled,
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
                    "basic_auth_encrypted": encrypted_password if auth_enabled else None,
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
    session: SessionDep,
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
    session: SessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
) -> None:
    """
    Failure callback endpoint called by Airflow DAG on failure.
    Deletes the IntegrityLink and drops the staging table.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)

    Returns:
        Success message with cleanup details
    """
    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Get staging table name
    staging_table_name = integrity_link.staging_table_name

    # Drop the staging table if it exists
    if staging_table_name:
        try:
            # CRITICAL: Validate table name before using in SQL (defense in depth)
            from data_manipulation.validators import validate_table_name

            validated_table_name = validate_table_name(staging_table_name, context="staging")

            schema = "staging"  # FIXME get it from config
            metadata = MetaData(schema=schema)
            table = Table(validated_table_name, metadata)
            table.drop(session.get_bind(), checkfirst=True)
            session.commit()
        except ValueError as e:
            # Log validation error but continue with cleanup
            logger.error(f"Invalid staging table name in database: {e}")
        except Exception as e:
            # Log the error but continue with IntegrityLink deletion
            logger.error(f"Error dropping staging table {staging_table_name}: {e}")

    # Delete the IntegrityLink
    session.delete(integrity_link)
    session.commit()


@router.get("/{integrity_link_id}/metadata")
def get_staging_metadata(
    session: SessionDep,
    integrity_link_id: str,
) -> StagingMetadataResponse:
    """
    Get metadata of the staging table.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)

    Returns:
        Metadata of the staging table
    """

    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    staging_table_name = integrity_link.staging_table_name
    source_import_type = integrity_link.source_import_type
    source_file_name = integrity_link.source_file_name
    source_file_type = integrity_link.source_file_type

    schema = "staging"  # FIXME get it from config
    sql_metadata = MetaData(schema=schema)
    table = Table(staging_table_name, sql_metadata, autoload_with=session.get_bind())

    columns = [ColumnMetadata(name=col.name) for col in table.columns]
    row_count = session.scalar(select(func.count()).select_from(table)) or 0

    return StagingMetadataResponse(
        title=source_file_name or "",
        import_type=source_import_type,
        file_type=source_file_type,
        columns=columns,
        row_count=row_count,
    )


@router.get("/{integrity_link_id}/preview")
def get_staging_preview(
    session: SessionDep,
    integrity_link_id: str,
    limit: int = Query(10, description="Number of rows to preview"),
) -> StagingPreviewResponse:
    """
    Get a preview of the data in the staging table.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        limit: Number of rows to preview (optional, default is 10)

    Returns:
        Preview data from the staging table
    """

    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    staging_table_name = integrity_link.staging_table_name
    if not staging_table_name:
        raise HTTPException(status_code=500, detail="Staging table name is missing")

    schema = "staging"  # FIXME get it from config
    metadata = MetaData(schema=schema)
    table = Table(staging_table_name, metadata, autoload_with=session.get_bind())
    query = select(table).limit(limit)

    subset = session.execute(query).mappings()  # type: ignore[misc]

    return StagingPreviewResponse(
        data=[dict(row) for row in subset],
    )
