"""Dataset administration: export/import across platforms, ownership change, deletion."""

from datetime import datetime, timezone
from uuid import UUID

from data_manipulation.database import create_schema, table_exists
from data_manipulation.validators import validate_schema_name
from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import or_, text
from sqlmodel import col, select

from src.api.deps import (
    DatafeederSessionDep,
    GeorchestraContextDep,
    GeoServerServiceDep,
    MetadataServiceDep,
)
from src.api.routes.ingestion.integrity_link import (
    _sync_data_sharing,  # pyright: ignore[reportPrivateUsage]
)
from src.core.callback import build_callback_url
from src.core.config import get_data_schema, get_settings
from src.core.constants import DEFAULT_DATA_SCHEMA
from src.core.db import data_engine
from src.core.encryption import encrypt_basic_auth
from src.core.logging import get_logger
from src.core.run_ids import make_manual_process_run_id
from src.core.task_executor import ProcessSource, TaskExecutorType
from src.models.data_import import (
    ImportType,
    IntegrityLinkExport,
    IntegrityLinkImportMode,
    IntegrityLinkImportRequest,
    IntegrityLinkImportResponse,
    IntegrityLinkOwnershipRequest,
    IntegrityLinkResponse,
)
from src.models.integrity_link import IntegrityLink
from src.models.recurrence import RecurrencePreset
from src.services.airflow_client import cancel_dataset_runs
from src.services.console_service import ConsoleService
from src.services.dataset_deletion_service import DatasetDeletionService
from src.services.executor_factory import get_task_executor
from src.services.georchestra import GeorchestraContext
from src.services.geoserver import GeoServerService
from src.services.layer_publication import (
    DatastoreSchemaMismatchError,
    publish_final_table,
    read_table_extent,
)
from src.services.metadata_service import MetadataService

# Mounted under /internal; hidden from the OpenAPI schema used by the Angular client
router = APIRouter(prefix="/ingestion/integrity-link", tags=["Ingestion"], include_in_schema=False)
logger = get_logger()

# FILE is excluded: its source is in the storage of the exporting platform
REPROCESSABLE_IMPORT_TYPES = {ImportType.URL, ImportType.API, ImportType.FTP, ImportType.DATABASE}
# No final table managed by datafeeder
LINK_ONLY_IMPORT_TYPES = {ImportType.EMPTY, ImportType.PREFILLED}


def _require_administrator(geo_ctx: GeorchestraContext) -> None:
    if not geo_ctx.is_administrator():
        raise HTTPException(status_code=403, detail="Administrator role required")


def _get_integrity_link(session: DatafeederSessionDep, integrity_link_id: UUID) -> IntegrityLink:
    integrity_link = session.get(IntegrityLink, integrity_link_id)
    if integrity_link is None:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")
    return integrity_link


def _require_console_owner(owner: str, organization: str) -> None:
    console_service = ConsoleService(get_settings().CONSOLE_INTERNAL_URL)
    if console_service.get_organization(organization) is None:
        raise HTTPException(status_code=400, detail=f"Unknown organization '{organization}'")
    if owner not in console_service.fetch_users_by_usernames([owner]):
        raise HTTPException(status_code=400, detail=f"Unknown user '{owner}'")


@router.get(
    "/{integrity_link_id}/export",
    response_model=IntegrityLinkExport,
    summary="Export a dataset definition",
    description=(
        "Administrators only. Dataset definition to import on another platform. "
        "Permission rules, publication state and source password are not exported."
    ),
)
def export_integrity_link(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: UUID,
) -> IntegrityLinkExport:
    _require_administrator(geo_ctx)
    integrity_link = _get_integrity_link(session, integrity_link_id)
    return IntegrityLinkExport.model_validate(integrity_link).model_copy(
        update={
            "has_source_password": integrity_link.source_password_encrypted is not None,
            "preset_id": (
                RecurrencePreset.from_cron(integrity_link.schedule)
                if integrity_link.schedule
                else None
            ),
        }
    )


def _resolve_import_mode(
    request: IntegrityLinkImportRequest,
    session: DatafeederSessionDep,
    metadata_service: MetadataService,
) -> IntegrityLinkImportMode:
    """Validate the import (without writing) and choose ATTACH or REPROCESS."""
    exported = request.link
    import_type = exported.source_import_type
    if not exported.metadata_id:
        raise HTTPException(status_code=400, detail="The exported dataset has no metadata record")
    if import_type not in LINK_ONLY_IMPORT_TYPES and not exported.final_table_name:
        raise HTTPException(
            status_code=400, detail="The exported dataset has never been processed (no table)"
        )
    if exported.has_source_password and not request.source_password:
        raise HTTPException(status_code=400, detail="source_password is required for this dataset")
    if request.source_password and not exported.source_username:
        raise HTTPException(
            status_code=400, detail="source_password given but the dataset has no source_username"
        )
    if (
        request.copy_recurrence
        and exported.schedule
        and import_type not in REPROCESSABLE_IMPORT_TYPES
    ):
        raise HTTPException(
            status_code=400,
            detail=f"The recurrence of a '{import_type.value}' dataset cannot run on this platform",
        )
    if request.copy_recurrence and exported.schedule and not exported.preset_id:
        raise HTTPException(
            status_code=400,
            detail=f"The recurrence '{exported.schedule}' is not a recurrence preset",
        )

    conditions = [
        col(IntegrityLink.id) == exported.id,
        col(IntegrityLink.metadata_id) == exported.metadata_id,
    ]
    if exported.final_table_name:
        conditions.append(col(IntegrityLink.final_table_name) == exported.final_table_name)
    conflict = session.exec(select(IntegrityLink).where(or_(*conditions))).first()
    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"Dataset {conflict.id} already uses this id, metadata record or table name",
        )

    try:
        record_exists = metadata_service.record_exists(exported.metadata_id)
    except Exception as e:
        logger.error(f"GeoNetwork check failed for record {exported.metadata_id}: {e}")
        raise HTTPException(status_code=502, detail="GeoNetwork is unreachable")
    if not record_exists:
        raise HTTPException(
            status_code=400,
            detail=f"Metadata record {exported.metadata_id} not found in GeoNetwork: "
            "copy it to this platform first (e.g. with maelstro)",
        )

    if import_type in LINK_ONLY_IMPORT_TYPES:
        return IntegrityLinkImportMode.ATTACH
    assert exported.final_table_name
    target_schema = get_data_schema(exported.integrity_organization.lower())
    if table_exists(data_engine, target_schema, exported.final_table_name):
        return IntegrityLinkImportMode.ATTACH
    if import_type in REPROCESSABLE_IMPORT_TYPES and exported.source_url:
        return IntegrityLinkImportMode.REPROCESS
    raise HTTPException(
        status_code=400,
        detail=f"Table {target_schema}.{exported.final_table_name} not found and a "
        f"'{import_type.value}' dataset cannot be re-ingested from its source: "
        "copy its data to this platform first (e.g. with maelstro)",
    )


async def _attach_layer(integrity_link: IntegrityLink, geoserver_service: GeoServerService) -> None:
    """Set data_id to the layer of the copied table, publishing it if missing."""
    table_name = integrity_link.final_table_name
    assert table_name
    workspace = integrity_link.integrity_organization.lower()
    if geoserver_service.layer_exists(workspace, f"{workspace}_ds", table_name):
        integrity_link.data_id = f"{workspace}:{table_name}"
        return
    target_schema = get_data_schema(workspace)
    try:
        extent = read_table_extent(table_name, target_schema)
        await publish_final_table(
            geoserver_service, integrity_link, table_name, target_schema, extent
        )
    except DatastoreSchemaMismatchError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to publish {workspace}:{table_name}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Failed to publish the GeoServer layer")


def _trigger_reprocess(
    integrity_link: IntegrityLink, encrypted_password: str | None
) -> IntegrityLinkImportResponse:
    """Re-ingest the dataset from its source with process_dag."""
    assert integrity_link.source_url and integrity_link.final_table_name
    integrity_link_id = str(integrity_link.id)
    dag_run_id = make_manual_process_run_id(
        integrity_link_id, int(datetime.now(timezone.utc).timestamp())
    )
    target_schema = get_data_schema(integrity_link.integrity_organization.lower())
    callback_params = {
        "integrity_link_id": integrity_link_id,
        "final_table_name": integrity_link.final_table_name,
        "dag_id": "process_dag",
        "dag_run_id": dag_run_id,
        "target_schema": target_schema,
    }
    task_info = get_task_executor().trigger_process_task(
        run_id=dag_run_id,
        final_table_name=integrity_link.final_table_name,
        integrity_transformation=integrity_link.integrity_transformation or {},
        success_callback_url=build_callback_url(
            "/internal/ingestion/process/dag_success", callback_params
        ),
        failure_callback_url=build_callback_url(
            "/internal/ingestion/process/dag_failure", callback_params
        ),
        target_schema=target_schema,
        source=ProcessSource(
            source=integrity_link.source_url,
            source_type=integrity_link.source_import_type.value.upper(),
            source_layer=integrity_link.source_layer,
            source_protocol=integrity_link.source_protocol,
            encrypted_credentials=encrypted_password,
        ),
    )
    return IntegrityLinkImportResponse(
        integrity_link_id=integrity_link_id,
        mode=IntegrityLinkImportMode.REPROCESS,
        dag_id=task_info.task_id,
        dag_run_id=task_info.run_id,
        status=task_info.status,
    )


@router.post(
    "/import",
    response_model=IntegrityLinkImportResponse,
    status_code=201,
    summary="Import a dataset exported from another platform",
    description=(
        "Administrators only. The metadata record must already be in GeoNetwork. 'attach' "
        "mode if the final table is already here, otherwise 'reprocess' from the source "
        "(impossible for files). A failed reprocess leaves the dataset without data: delete "
        "it before retrying. The dataset starts unpublished."
    ),
)
async def import_integrity_link(
    request: IntegrityLinkImportRequest,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    geoserver_service: GeoServerServiceDep,
    metadata_service: MetadataServiceDep,
) -> IntegrityLinkImportResponse:
    _require_administrator(geo_ctx)
    _require_console_owner(request.link.integrity_owner, request.link.integrity_organization)
    mode = _resolve_import_mode(request, session, metadata_service)
    exported = request.link

    encrypted_password = None
    if request.source_password and exported.source_username:
        encrypted_password = encrypt_basic_auth(
            session.connection(), exported.source_username, request.source_password
        )

    schedule = None
    if request.copy_recurrence and exported.preset_id:
        # Local cron of the preset: the execution hour may differ
        schedule = exported.preset_id.cron

    integrity_link = IntegrityLink(
        id=exported.id,
        metadata_id=exported.metadata_id,
        integrity_title=exported.integrity_title,
        integrity_owner=exported.integrity_owner,
        integrity_organization=exported.integrity_organization,
        integrity_transformation=exported.integrity_transformation,
        source_import_type=exported.source_import_type,
        source_url=exported.source_url,
        source_layer=exported.source_layer,
        source_protocol=exported.source_protocol,
        source_file_name=exported.source_file_name,
        source_file_type=exported.source_file_type,
        source_username=exported.source_username,
        source_password_encrypted=encrypted_password,
        final_table_name=exported.final_table_name,
        schedule=schedule,
        schedule_enabled=schedule is not None,
    )
    if mode == IntegrityLinkImportMode.ATTACH:
        integrity_link.data_id = exported.data_id
        if exported.final_table_name and exported.source_import_type not in LINK_ONLY_IMPORT_TYPES:
            await _attach_layer(integrity_link, geoserver_service)
            # Marks the table as already ingested
            integrity_link.last_retrieval_timestamp = exported.last_retrieval_timestamp or (
                datetime.now(timezone.utc)
            )

    session.add(integrity_link)
    session.commit()
    session.refresh(integrity_link)
    logger.info(
        f"Imported IntegrityLink {integrity_link.id} (metadata {exported.metadata_id}, "
        f"mode {mode.value})"
    )

    try:
        metadata_service.set_record_ownership(integrity_link)
    except Exception as e:
        logger.warning(f"Failed to set metadata ownership for {integrity_link.id}: {e}")

    if mode == IntegrityLinkImportMode.ATTACH:
        return IntegrityLinkImportResponse(
            integrity_link_id=str(integrity_link.id), mode=IntegrityLinkImportMode.ATTACH
        )
    try:
        return _trigger_reprocess(integrity_link, encrypted_password)
    except Exception as e:
        logger.error(f"Failed to trigger process for imported {integrity_link.id}: {e}")
        session.delete(integrity_link)
        session.commit()
        raise HTTPException(status_code=500, detail=f"Task execution error: {e}")


def _move_table(table_name: str, from_schema: str, to_schema: str) -> None:
    if from_schema == to_schema:
        return
    validate_schema_name(from_schema)
    validate_schema_name(to_schema)
    create_schema(data_engine, to_schema)
    with data_engine.begin() as conn:
        conn.execute(text(f'ALTER TABLE "{from_schema}"."{table_name}" SET SCHEMA "{to_schema}"'))
    logger.info(f"Moved table {table_name} from schema {from_schema} to {to_schema}")


def _locate_final_table(
    integrity_link: IntegrityLink, current_ws: str, geoserver_service: GeoServerService
) -> str | None:
    """Schema of the final table, which a USE_ORG_SCHEMA change may have left elsewhere."""
    table_name = integrity_link.final_table_name
    assert table_name
    candidates = [
        geoserver_service.get_datastore_schema(current_ws, f"{current_ws}_ds"),
        get_data_schema(integrity_link.integrity_organization),
        DEFAULT_DATA_SCHEMA,
        current_ws,
    ]
    for schema in dict.fromkeys(c for c in candidates if c):
        if table_exists(data_engine, schema, table_name):
            return schema
    return None


def _sync_data_sharing_safe(
    session: DatafeederSessionDep, integrity_link: IntegrityLink, geoserver: GeoServerService
) -> None:
    try:
        _sync_data_sharing(session, str(integrity_link.id), integrity_link, geoserver)
    except Exception as e:
        logger.error(f"Failed to sync GeoServer ACL of {integrity_link.id}: {e}", exc_info=True)


def _update_record_layer_links(
    integrity_link: IntegrityLink,
    old_layer_name: str,
    is_geographic: bool,
    geoserver_service: GeoServerService,
    metadata_service: MetadataService,
) -> None:
    """Point the record layer links to the moved layer (soft failure)."""
    if not integrity_link.metadata_id:
        return
    table_name = old_layer_name.split(":", 1)[1]
    try:
        layer_urls = geoserver_service.build_layer_urls_for_metadata(
            workspace_name=integrity_link.integrity_organization.lower(),
            table_name=table_name,
            is_geographic=is_geographic,
        )
        metadata_service.read_schema_from_gn(
            integrity_link.metadata_id
        ).replace_layer_online_resources(old_layer_name, layer_urls).upload_to_gn()
    except Exception as e:
        logger.warning(
            f"Failed to update the layer links of record {integrity_link.metadata_id}: {e}",
            exc_info=True,
        )


def _check_datastore_schema(
    workspace: str, schema: str, geoserver_service: GeoServerService
) -> None:
    datastore_schema = geoserver_service.get_datastore_schema(workspace, f"{workspace}_ds")
    if datastore_schema is not None and datastore_schema != schema:
        raise HTTPException(
            status_code=409,
            detail=f"Datastore {workspace}_ds reads schema '{datastore_schema}' instead of "
            f"'{schema}': fix the datastore of this workspace first",
        )


async def _move_dataset(
    integrity_link: IntegrityLink,
    new_organization: str,
    session: DatafeederSessionDep,
    geoserver_service: GeoServerService,
    metadata_service: MetadataService,
) -> None:
    """Move the final table and layer to the schema and workspace of the new organization.

    The caller commits. On GeoServer failure, the table is moved back (502).
    """
    old_organization = integrity_link.integrity_organization
    table_name = integrity_link.final_table_name
    assert table_name
    parts = integrity_link.parse_data_id()
    current_ws = parts[0].lower() if parts else old_organization.lower()
    new_ws = new_organization.lower()
    current_schema = _locate_final_table(integrity_link, current_ws, geoserver_service)
    new_schema = get_data_schema(new_ws)

    if current_schema is None:
        raise HTTPException(
            status_code=409,
            detail=f"Final table {table_name} not found: the dataset cannot be moved",
        )
    if (current_schema, current_ws) == (new_schema, new_ws):
        integrity_link.integrity_organization = new_organization
        return
    _check_datastore_schema(new_ws, new_schema, geoserver_service)
    if current_schema != new_schema and table_exists(data_engine, new_schema, table_name):
        raise HTTPException(
            status_code=409, detail=f"Table {new_schema}.{table_name} already exists"
        )
    if current_ws != new_ws and geoserver_service.layer_exists(new_ws, f"{new_ws}_ds", table_name):
        raise HTTPException(
            status_code=409, detail=f"GeoServer layer {new_ws}:{table_name} already exists"
        )
    extent = read_table_extent(table_name, current_schema)

    if get_settings().TASK_EXECUTOR == TaskExecutorType.AIRFLOW:
        try:
            cancel_dataset_runs(str(integrity_link.id))
        except Exception as e:
            logger.error(f"Failed to cancel DAG runs of {integrity_link.id}: {e}")
            raise HTTPException(
                status_code=502,
                detail="Failed to cancel the running DAG runs of the dataset: not moved",
            )

    _move_table(table_name, current_schema, new_schema)
    integrity_link.integrity_organization = new_organization
    if current_ws == new_ws:
        return

    # Before removing the old layer, which a failure leaves in place
    try:
        await publish_final_table(geoserver_service, integrity_link, table_name, new_schema, extent)
    except Exception as e:
        logger.error(f"Failed to publish {table_name} in workspace {new_ws}: {e}", exc_info=True)
        integrity_link.integrity_organization = old_organization
        try:
            _move_table(table_name, new_schema, current_schema)
        except Exception as restore_error:
            logger.error(
                f"Failed to move {table_name} back to {current_schema}: {restore_error}",
                exc_info=True,
            )
        raise HTTPException(
            status_code=502, detail="Failed to publish the layer in the new organization"
        )

    geoserver_service.delete_layer(current_ws, f"{current_ws}_ds", table_name)
    geoserver_service.delete_layer_acl(current_ws, table_name)
    _sync_data_sharing_safe(session, integrity_link, geoserver_service)
    _update_record_layer_links(
        integrity_link,
        f"{current_ws}:{table_name}",
        extent.is_geographic,
        geoserver_service,
        metadata_service,
    )


@router.put(
    "/{integrity_link_id}/ownership",
    response_model=IntegrityLinkResponse,
    summary="Reassign a dataset to another owner and organization",
    description=(
        "Administrators only. Without organization, only the owner changes. A new "
        "organization moves the table to its schema and the layer to its workspace, and "
        "updates the record links. 409 if the table is missing, a "
        "name is taken or the target datastore reads another schema. Prefilled datasets: "
        "only the dataset is reassigned."
    ),
)
async def reassign_integrity_link_ownership(
    integrity_link_id: UUID,
    request: IntegrityLinkOwnershipRequest,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    geoserver_service: GeoServerServiceDep,
    metadata_service: MetadataServiceDep,
) -> IntegrityLinkResponse:
    _require_administrator(geo_ctx)
    integrity_link = _get_integrity_link(session, integrity_link_id)
    current = integrity_link.integrity_organization
    org_changes = bool(request.organization) and request.organization.lower() != current.lower()
    organization = request.organization if org_changes and request.organization else current
    _require_console_owner(request.owner, organization)

    # Layer and record of a prefilled dataset are not managed by datafeeder
    is_prefilled = integrity_link.source_import_type == ImportType.PREFILLED
    if org_changes and integrity_link.final_table_name and not is_prefilled:
        await _move_dataset(
            integrity_link, organization, session, geoserver_service, metadata_service
        )
    else:
        integrity_link.integrity_organization = organization
    integrity_link.integrity_owner = request.owner
    session.add(integrity_link)
    session.commit()
    session.refresh(integrity_link)
    logger.info(f"Reassigned IntegrityLink {integrity_link.id} to {request.owner} / {organization}")

    if integrity_link.metadata_id and not is_prefilled:
        try:
            metadata_service.set_record_ownership(integrity_link)
        except Exception as e:
            logger.warning(f"Failed to set metadata ownership for {integrity_link.id}: {e}")

    return IntegrityLinkResponse.model_validate(integrity_link)


@router.delete(
    "/{integrity_link_id}",
    status_code=204,
    summary="Delete a dataset, keeping its layer and metadata record by default",
    description=(
        "Administrators only. The layer, final table and GeoNetwork record are kept "
        "unless requested."
    ),
)
def delete_integrity_link_admin(
    integrity_link_id: UUID,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    geoserver_service: GeoServerServiceDep,
    metadata_service: MetadataServiceDep,
    delete_layer: bool = Query(
        False, description="Also delete the GeoServer layer and the final table"
    ),
    delete_metadata: bool = Query(False, description="Also delete the GeoNetwork record"),
) -> Response:
    _require_administrator(geo_ctx)
    integrity_link = _get_integrity_link(session, integrity_link_id)
    try:
        DatasetDeletionService(geoserver_service, metadata_service).delete_dataset(
            integrity_link,
            session,
            delete_layer=delete_layer,
            delete_metadata=delete_metadata,
        )
    except Exception as e:
        logger.error(f"Failed to delete dataset {integrity_link_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {e}")
    return Response(status_code=204)
