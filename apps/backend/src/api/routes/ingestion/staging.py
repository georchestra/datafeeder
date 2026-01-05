import re
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import requests
from airflow_client.client.models.trigger_dag_run_post_body import TriggerDAGRunPostBody
from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy import MetaData, Table, func, select

from src.api.deps import SessionDep
from src.core.callback import build_callback_url
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
from src.services.files import upload_file_to_temp

router = APIRouter(prefix="/ingestion/staging", tags=["Ingestion"])
logger = get_logger()


def _generate_staging_table_name(dag_run_id: str) -> str:
    """Generate a unique, readable staging table name from an Airflow DAG run ID.

    Args:
        dag_run_id: The Airflow DAG run ID

    Returns:
        A unique staging table name
    """
    # TODO: could be nice to have more readable names (extract filename if possible)
    # HttpURL: Head request ?
    # FileUrl: use path name directly ?

    # Generate short hash for uniqueness (encode the full URL)
    return f"staging_{dag_run_id.replace('-', '_')[:32]}"


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
    staging_table_name = _generate_staging_table_name(dag_run_id)

    source_file_name = None
    source_file_type = None

    # Extract source according to import type
    match type:
        case ImportType.FILE:
            if file is None:
                raise HTTPException(status_code=400, detail="File is required")
            
            source = await upload_file_to_temp(file)
        case ImportType.URL:
            if not url:
                raise HTTPException(status_code=400, detail="URL is required for URL import type")

            source = url

            try:
                head_response = requests.head(url)
                head_response.raise_for_status()

                content_disposition = head_response.headers.get("content-disposition")
                if content_disposition:
                    fname = re.findall("filename=(.+)", content_disposition)
                    if fname:
                        source_file_name = fname[0].strip('"')
                    else:
                        fname_utf8 = re.findall("filename\\*=UTF-8''(.+)", content_disposition)
                        if fname_utf8:
                            source_file_name = fname_utf8[0]
                
                content_type = head_response.headers.get("content-type")
                if content_type:
                    if "application/json+geo" in content_type:
                        source_file_type = FileType.GEOJSON
                    elif "text/csv" in content_type:
                        source_file_type = FileType.CSV
                    elif "application/zip" in content_type:
                        source_file_type = FileType.SHAPEFILE
                    else:
                        raise HTTPException(
                            status_code=400, detail=f"Unsupported content type: {content_type}"
                        )

            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Error accessing URL: {e}")

        case ImportType.DATABASE | ImportType.API:
            # TODO: implement handling for DATABASE and API import types
            raise HTTPException(
                status_code=501, detail=f"Import type {type.value} not implemented yet"
            )

    # Create IntegrityLink immediately
    integrity_link = IntegrityLink(
        integrity_owner=sec_username,
        integrity_organization=sec_org,
        source_import_type=type,
        source_url=url,
        source_file_name=source_file_name,
        source_file_type=source_file_type,
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
    try:
        if not staging_table_name:
            raise Exception("Staging table name is missing in IntegrityLink")

        schema = "staging"  # FIXME get it from config
        metadata = MetaData(schema=schema)
        table = Table(staging_table_name, metadata)
        table.drop(session.get_bind(), checkfirst=True)
        session.commit()
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
    if not staging_table_name:
        raise HTTPException(status_code=500, detail="Staging table name is missing")

    source_import_type = integrity_link.source_import_type
    if not source_import_type:
        raise HTTPException(
            status_code=500, detail="Source import type is missing in IntegrityLink"
        )

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
