"""Administration of datasets: replication across platforms (export/import), ownership
reassignment and deletion keeping the published data and metadata."""

from datetime import datetime, timezone

from data_manipulation.database import create_schema, table_exists
from data_manipulation.validators import validate_schema_name
from fastapi import APIRouter, HTTPException, Query, Response
from sqlalchemy import or_, text
from sqlmodel import col, select

from src.api.deps import (
    DatafeederSessionDep,
    GeorchestraContextDep,
    GeoServerServiceDep,
    GroupIdsDep,
    MetadataServiceDep,
)
from src.api.routes.ingestion.integrity_link import (
    _sync_data_sharing,  # pyright: ignore[reportPrivateUsage]
)
from src.core.callback import build_callback_url
from src.core.config import get_data_schema, get_settings
from src.core.db import data_engine
from src.core.encryption import encrypt_basic_auth
from src.core.logging import get_logger
from src.core.run_ids import make_manual_process_run_id
from src.core.security import AccessLevel, load_authorized_integrity_link
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
from src.services.layer_publication import publish_final_table, read_table_extent
from src.services.metadata_service import MetadataService

# Administration routes, mounted under /internal (gateway restricts to ADMINISTRATOR).
# Excluded from the schema so the Angular client never generates wrappers for them.
router = APIRouter(prefix="/ingestion/integrity-link", tags=["Ingestion"], include_in_schema=False)
logger = get_logger()

# Import types process_dag can re-ingest from the target platform. FILE sources point
# to the internal file storage of the exporting platform, out of reach from the target one.
REPROCESSABLE_IMPORT_TYPES = {ImportType.URL, ImportType.API, ImportType.FTP, ImportType.DATABASE}
# Import types without a final table managed by datafeeder: only the link is registered
LINK_ONLY_IMPORT_TYPES = {ImportType.EMPTY, ImportType.PREFILLED}


def _require_administrator(geo_ctx: GeorchestraContext) -> None:
    if not geo_ctx.is_administrator():
        raise HTTPException(status_code=403, detail="Administrator role required")


@router.get(
    "/{integrity_link_id}/export",
    response_model=IntegrityLinkExport,
    summary="Export a dataset definition",
    description=(
        "Portable description of the dataset (source, transformation, recurrence, metadata "
        "record UUID, final table), to replicate it on another platform with POST /internal/ingestion/integrity-link/import. "
        "Permission rules, publication state and the source password are not exported."
    ),
)
def export_integrity_link(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
    integrity_link_id: str,
) -> IntegrityLinkExport:
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, geo_ctx, session, group_ids
    )
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
    """Check the exported dataset can be imported here and pick the import mode. Writes nothing.

    ATTACH when the data is already on this platform (or the dataset has none), REPROCESS when
    it is absent but can be re-ingested from the source. A FILE dataset without its table here
    is rejected: its data has to be copied first (e.g. with maelstro).
    """
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
    """Point data_id to the layer of the copied table, publishing it if it was not copied."""
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
        "Administrators only. Registers the dataset with the exported id, owner, organization, "
        "source and transformation. The metadata record must already exist in GeoNetwork with "
        "the exported UUID. If the final table is already on this platform (copied e.g. with "
        "maelstro), the dataset is attached to it (mode 'attach'), its GeoServer layer being "
        "published if missing. Otherwise the dataset is re-ingested from its source by the "
        "process DAG (mode 'reprocess'), which is not possible for a file import: its data has "
        "to be copied first. Permission rules are not imported: the dataset starts unpublished."
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
    mode = _resolve_import_mode(request, session, metadata_service)
    exported = request.link

    encrypted_password = None
    if request.source_password and exported.source_username:
        encrypted_password = encrypt_basic_auth(
            session.connection(), exported.source_username, request.source_password
        )

    schedule = None
    if request.copy_recurrence and exported.schedule:
        # Cron of the preset on this platform (the execution hour may differ), else as is
        schedule = exported.preset_id.cron if exported.preset_id else exported.schedule

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
            # A non-null timestamp marks the table as already ingested (re-runs replace it)
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

    # Ownership of the copied record — soft failure, as for a regular process
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


async def _move_dataset(
    integrity_link: IntegrityLink,
    new_organization: str,
    session: DatafeederSessionDep,
    geoserver_service: GeoServerService,
) -> None:
    """Move the final table and GeoServer layer of a dataset to another organization.

    Updates integrity_organization and data_id; the caller commits. On GeoServer failure,
    the previous location is restored and HTTP 502 is raised.
    """
    old_organization = integrity_link.integrity_organization
    old_ws, new_ws = old_organization.lower(), new_organization.lower()
    table_name = integrity_link.final_table_name
    assert table_name
    old_schema, new_schema = get_data_schema(old_ws), get_data_schema(new_ws)

    if not table_exists(data_engine, old_schema, table_name):
        # Never processed, or failed: there is no data to move
        integrity_link.integrity_organization = new_organization
        return
    if old_schema != new_schema and table_exists(data_engine, new_schema, table_name):
        raise HTTPException(
            status_code=409, detail=f"Table {new_schema}.{table_name} already exists"
        )
    if geoserver_service.layer_exists(new_ws, f"{new_ws}_ds", table_name):
        raise HTTPException(
            status_code=409, detail=f"GeoServer layer {new_ws}:{table_name} already exists"
        )
    extent = read_table_extent(table_name, old_schema)

    # No run may keep writing to the old location while the dataset moves
    if get_settings().TASK_EXECUTOR == TaskExecutorType.AIRFLOW:
        try:
            cancel_dataset_runs(str(integrity_link.id))
        except Exception as e:
            logger.warning(f"Failed to cancel DAG runs of {integrity_link.id}: {e}")

    _move_table(table_name, old_schema, new_schema)
    geoserver_service.delete_layer(old_ws, f"{old_ws}_ds", table_name)
    geoserver_service.delete_layer_acl(old_ws, table_name)
    integrity_link.integrity_organization = new_organization
    try:
        await publish_final_table(geoserver_service, integrity_link, table_name, new_schema, extent)
    except Exception as e:
        logger.error(f"Failed to publish {table_name} in workspace {new_ws}: {e}", exc_info=True)
        # Restore the previous location so the dataset stays usable
        integrity_link.integrity_organization = old_organization
        try:
            _move_table(table_name, new_schema, old_schema)
            await publish_final_table(
                geoserver_service, integrity_link, table_name, old_schema, extent
            )
        except Exception as restore_error:
            logger.error(
                f"Failed to restore {table_name} in {old_schema} / workspace {old_ws}: "
                f"{restore_error}",
                exc_info=True,
            )
        raise HTTPException(
            status_code=502, detail="Failed to publish the layer in the new organization"
        )

    geoserver_service.delete_datastore_if_empty(old_ws, f"{old_ws}_ds")
    geoserver_service.delete_workspace_if_empty(old_ws)

    # ACL rules are keyed by layer name: apply the dataset DATA rules to the new layer
    try:
        _sync_data_sharing(session, str(integrity_link.id), integrity_link, geoserver_service)
    except Exception as e:
        logger.error(f"Failed to sync GeoServer ACL of {integrity_link.id}: {e}", exc_info=True)


@router.put(
    "/{integrity_link_id}/ownership",
    response_model=IntegrityLinkResponse,
    summary="Reassign a dataset to another owner and organization",
    description=(
        "Administrators only. The owner must be a console user and the organization a console "
        "organization. When the organization changes, the final table moves to the schema of "
        "the new organization (if schemas are per organization), the GeoServer layer is "
        "recreated in its workspace (permission rules re-applied), running DAG runs are "
        "cancelled. The layer URLs of the metadata record are left as is. The record "
        "ownership follows the new owner and organization."
    ),
)
async def reassign_integrity_link_ownership(
    integrity_link_id: str,
    request: IntegrityLinkOwnershipRequest,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
    geoserver_service: GeoServerServiceDep,
    metadata_service: MetadataServiceDep,
) -> IntegrityLinkResponse:
    _require_administrator(geo_ctx)
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, geo_ctx, session, group_ids
    )

    console_service = ConsoleService(get_settings().CONSOLE_INTERNAL_URL)
    if console_service.get_organization(request.organization) is None:
        raise HTTPException(
            status_code=400, detail=f"Unknown organization '{request.organization}'"
        )
    if request.owner not in console_service.fetch_users_by_usernames([request.owner]):
        raise HTTPException(status_code=400, detail=f"Unknown user '{request.owner}'")

    organization_changes = (
        integrity_link.integrity_organization.lower() != request.organization.lower()
    )
    # A prefilled dataset references a layer datafeeder does not manage: never moved
    if (
        organization_changes
        and integrity_link.final_table_name
        and integrity_link.source_import_type != ImportType.PREFILLED
    ):
        await _move_dataset(integrity_link, request.organization, session, geoserver_service)
    else:
        integrity_link.integrity_organization = request.organization
    integrity_link.integrity_owner = request.owner
    session.add(integrity_link)
    session.commit()
    session.refresh(integrity_link)
    logger.info(
        f"Reassigned IntegrityLink {integrity_link.id} to {request.owner} / {request.organization}"
    )

    if integrity_link.metadata_id:
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
        "Administrators only. Deletes the dataset row (with its permission rules), its "
        "staging table and its Airflow DAG and run history. The published data (GeoServer "
        "layer and final table) and the GeoNetwork record are kept unless requested."
    ),
)
def delete_integrity_link_admin(
    integrity_link_id: str,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
    geoserver_service: GeoServerServiceDep,
    metadata_service: MetadataServiceDep,
    delete_layer: bool = Query(
        False, description="Also delete the GeoServer layer and the final table"
    ),
    delete_metadata: bool = Query(False, description="Also delete the GeoNetwork record"),
) -> Response:
    _require_administrator(geo_ctx)
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, geo_ctx, session, group_ids
    )
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
