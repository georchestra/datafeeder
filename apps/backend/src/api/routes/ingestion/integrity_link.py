from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query, Response
from sqlmodel import select

from src.api.deps import (
    DatafeederSessionDep,
    GeorchestraContextDep,
    GeoServerServiceDep,
    GroupIdsDep,
)
from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.security import (
    AccessLevel,
    load_authorized_integrity_link,
)
from src.models.data_import import (
    IntegrityLinkGsPublishResponse,
    IntegrityLinkResponse,
    UpdateMetadataGnRequest,
)
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import (
    GROUP_OR_ROLE_EVERYONE,
    IntegrityLinkRule,
    RuleType,
    RuleValue,
    UpsertRuleRequest,
)
from src.models.recurrence import RecurrencePreset
from src.services.console_service import ConsoleService, ConsoleServiceError
from src.services.dataset_deletion_service import DatasetDeletionService
from src.services.geoserver import (
    ACL_ROLE_EVERYONE,
    AclAccessType,
    GeoServerAclError,
    GeoServerService,
)
from src.services.metadata_service import MetadataService
from src.services.schedule_service import clear_schedule

logger = get_logger()

router = APIRouter(prefix="/ingestion/integrity-link", tags=["Ingestion"])


def _sync_metadata_sharing(
    session: DatafeederSessionDep,
    integrity_link_id: str,
    integrity_link: IntegrityLink,
) -> None:
    """Sync METADATA rules to GeoNetwork sharing privileges.

    Called after any rule mutation. Resolves group_or_role IDs to GeoNetwork group names
    via ConsoleService (organizations or roles depending on GN_SYNC_MODE), then delegates
    to MetadataService.sync_record_sharing.
    Skipped when integrity_link has no associated GeoNetwork record.

    Raises:
        HTTPException(500): If any group cannot be resolved or the GeoNetwork sync fails.
    """
    if not integrity_link.metadata_id:
        return

    settings = get_settings()

    all_rules = list(
        session.exec(
            select(IntegrityLinkRule).where(
                IntegrityLinkRule.integrity_link_id == UUID(integrity_link_id)
            )
        ).all()
    )

    try:
        console_service = ConsoleService(settings.CONSOLE_INTERNAL_URL)
        if settings.GN_SYNC_MODE == "ORG":
            items = console_service.get_all_organizations()
            groups_by_id = {
                item["id"].lower(): item["shortName"]
                for item in items
                if item.get("id") and item.get("shortName")
            }
        else:
            items = console_service.get_all_roles()
            groups_by_id = {
                item["id"].lower(): item["name"]
                for item in items
                if item.get("id") and item.get("name")
            }
    except Exception:
        logger.error("Failed to fetch groups from console for GN sync")
        raise HTTPException(status_code=500, detail="i18nerror.sync.geonetwork")

    resolved: list[tuple[str, RuleValue]] = []
    for rule in all_rules:
        if rule.rule_type != RuleType.METADATA:
            continue
        gn_group_name = groups_by_id.get(rule.group_or_role.lower())
        if not gn_group_name:
            logger.error("Could not resolve group '%s' for sharing sync", rule.group_or_role)
            raise HTTPException(status_code=500, detail="i18nerror.sync.geonetwork")
        resolved.append((gn_group_name, rule.rule_value))

    metadata_service = MetadataService(
        gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
        datadir_path=settings.DATADIR_PATH,
        credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
        gn_sync_mode=settings.GN_SYNC_MODE,
        verify_tls=False,
    )
    try:
        metadata_service.sync_record_sharing(integrity_link.metadata_id, resolved)
    except Exception:
        logger.error(
            "Failed to sync GN sharing for integrity_link %s",
            integrity_link_id,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="i18nerror.sync.geonetwork")


def _sync_data_sharing(
    session: DatafeederSessionDep,
    integrity_link_id: str,
    integrity_link: IntegrityLink,
    geoserver_service: GeoServerService | None = None,
) -> None:
    """Sync DATA rules to GeoServer layer ACL.

    Resolves role UUIDs to ROLE_xxx names via the Console API before syncing.
    Skipped when integrity_link has no published layer (final_table_name absent).

    Args:
        geoserver_service: Optional pre-built service instance. When None (default),
            a new instance is created from settings. Pass the injected service when
            calling from a route handler to allow test mocking.

    Raises:
        HTTPException(500): If role resolution or GeoServer ACL sync fails.
    """
    if not integrity_link.final_table_name:
        return

    all_rules = list(
        session.exec(
            select(IntegrityLinkRule).where(
                IntegrityLinkRule.integrity_link_id == UUID(integrity_link_id)
            )
        ).all()
    )

    settings = get_settings()

    data_rules = [rule for rule in all_rules if rule.rule_type == RuleType.DATA]
    uuids_to_resolve = {
        rule.group_or_role for rule in data_rules if rule.group_or_role != GROUP_OR_ROLE_EVERYONE
    }

    id_to_name: dict[str, str] = {}
    if uuids_to_resolve:
        # Only call Console when at least one non-EVERYONE role needs UUID resolution.
        # This keeps EVERYONE-only configs resilient to Console outages.
        console_service = ConsoleService(settings.CONSOLE_INTERNAL_URL)
        all_roles = console_service.get_all_roles()  # raises ConsoleServiceError on failure
        id_to_name = {
            str(r["id"]): f"ROLE_{r['name']}" for r in all_roles if r.get("id") and r.get("name")
        }

    resolved: list[tuple[str, RuleValue]] = []
    for rule in data_rules:
        if rule.group_or_role == GROUP_OR_ROLE_EVERYONE:
            resolved.append((ACL_ROLE_EVERYONE, rule.rule_value))
            continue
        role_name = id_to_name.get(rule.group_or_role)
        if not role_name:
            raise ConsoleServiceError(
                f"Could not resolve role '{rule.group_or_role}' for GeoServer ACL sync"
            )
        resolved.append((role_name, rule.rule_value))

    workspace = integrity_link.integrity_organization.lower()

    if geoserver_service is None:
        geoserver_service = GeoServerService(
            base_url=settings.GEOSERVER_INTERNAL_URL,
            username=settings.GEOSERVER_USER,
            password=settings.GEOSERVER_PASSWORD,
            public_url=settings.DATA_PUBLIC_URL,
        )
    geoserver_service.sync_layer_acl(workspace, integrity_link.final_table_name, resolved)


@router.get(
    "/{integrity_link_id}",
    response_model=IntegrityLinkResponse,
    summary="Get IntegrityLink by ID",
    description="Retrieve an IntegrityLink entity. The integrity_transformation field is excluded by default.",
)
def get_integrity_link(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: str,
    group_ids: GroupIdsDep,
    include_transformation: bool = Query(
        False,
        description="Include the integrity_transformation field in the response",
    ),
) -> IntegrityLinkResponse:
    """Get an IntegrityLink entity by its ID."""
    integrity_link, effective = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.METADATA_WRITE, geo_ctx, session, group_ids
    )

    preset = (
        RecurrencePreset.from_cron(integrity_link.schedule) if integrity_link.schedule else None
    )
    response = IntegrityLinkResponse.model_validate(integrity_link).model_copy(
        update={"access_level": effective.value, "preset_id": preset},
    )

    if not include_transformation:
        response.integrity_transformation = None

    return response


def _sync_title_geoserver(title: str, integrity_link: IntegrityLink) -> None:
    """Sync the metadata title to the corresponding GeoServer feature type layer."""
    if not integrity_link.final_table_name:
        return
    settings = get_settings()
    gs = GeoServerService(
        base_url=settings.GEOSERVER_INTERNAL_URL,
        username=settings.GEOSERVER_USER,
        password=settings.GEOSERVER_PASSWORD,
        public_url=settings.DATA_PUBLIC_URL,
    )
    workspace = integrity_link.integrity_organization.lower()
    datastore = f"{workspace}_ds"
    gs.update_layer_title(workspace, datastore, integrity_link.final_table_name, title)


@router.put(
    "/{integrity_link_id}/metadata-gn",
    response_model=IntegrityLinkResponse,
    summary="Save metadata to GeoNetwork and sync title",
    description=(
        "Receives the fully serialized metadata XML from the frontend, uploads it to GeoNetwork "
        "(OVERWRITE), then syncs the title to GeoServer (non blocking) and commits integrity_title "
        "to the database. DB is committed only when the GeoNetwork sync succeeds."
    ),
)
def update_metadata_gn(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: str,
    group_ids: GroupIdsDep,
    body: UpdateMetadataGnRequest,
) -> IntegrityLinkResponse:
    """Upload serialized metadata XML to GeoNetwork, then sync title to GeoServer and DB."""
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.METADATA_WRITE, geo_ctx, session, group_ids
    )

    settings = get_settings()
    metadata_service = MetadataService(
        gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
        datadir_path=settings.DATADIR_PATH,
        credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
        verify_tls=False,
    )

    try:
        metadata_service.upload_metadata_xml(body.serialized_xml.encode("utf-8"))
    except Exception as e:
        logger.error(
            "GeoNetwork upload failed for IntegrityLink %s: %s",
            integrity_link_id,
            e,
        )
        raise HTTPException(status_code=502, detail="i18nerror.save.geonetwork")

    try:
        _sync_title_geoserver(body.title, integrity_link)
    except Exception as e:
        logger.error(
            "GeoServer title sync failed for IntegrityLink %s: %s",
            integrity_link_id,
            e,
        )

    integrity_link.integrity_title = body.title
    session.add(integrity_link)
    session.flush()
    session.commit()
    session.refresh(integrity_link)

    return IntegrityLinkResponse.model_validate(integrity_link)


@router.get(
    "/{integrity_link_id}/rules",
    response_model=list[IntegrityLinkRule],
    summary="List rules for an IntegrityLink",
    description="Retrieve all rules associated with a given IntegrityLink.",
)
def list_integrity_link_rules(
    session: DatafeederSessionDep,
    georchestra_context: GeorchestraContextDep,
    integrity_link_id: str,
    group_ids: GroupIdsDep,
) -> list[IntegrityLinkRule]:
    """List all rules for a given IntegrityLink."""
    load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, georchestra_context, session, group_ids
    )

    statement = select(IntegrityLinkRule).where(
        IntegrityLinkRule.integrity_link_id == UUID(integrity_link_id)
    )
    return list(session.exec(statement).all())


@router.put(
    "/{integrity_link_id}/rules",
    response_model=IntegrityLinkRule,
    summary="Create or update a rule for an IntegrityLink",
)
def upsert_integrity_link_rule(
    session: DatafeederSessionDep,
    georchestra_context: GeorchestraContextDep,
    integrity_link_id: str,
    group_ids: GroupIdsDep,
    body: UpsertRuleRequest,
) -> IntegrityLinkRule:
    """Create or update a rule for a given IntegrityLink."""
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, georchestra_context, session, group_ids
    )

    statement = select(IntegrityLinkRule).where(
        IntegrityLinkRule.integrity_link_id == UUID(integrity_link_id),
        IntegrityLinkRule.group_or_role == body.group_or_role,
        IntegrityLinkRule.rule_type == body.rule_type,
    )
    existing_rule = session.exec(statement).first()

    if existing_rule:
        existing_rule.rule_value = body.rule_value
        session.add(existing_rule)
        session.flush()
        session.refresh(existing_rule)
        if body.rule_type == RuleType.DATA:
            try:
                _sync_data_sharing(session, integrity_link_id, integrity_link)
            except (GeoServerAclError, ConsoleServiceError) as e:
                logger.error(
                    "GeoServer sync failed while updating rule for IntegrityLink %s: %s",
                    integrity_link_id,
                    e,
                )
                session.rollback()
                raise HTTPException(status_code=500, detail="i18nerror.sync.geoserver")
        session.commit()
        _sync_metadata_sharing(session, integrity_link_id, integrity_link)
        return existing_rule

    new_rule = IntegrityLinkRule(
        integrity_link_id=UUID(integrity_link_id),
        group_or_role=body.group_or_role,
        rule_type=body.rule_type,
        rule_value=body.rule_value,
    )
    session.add(new_rule)
    session.flush()
    session.refresh(new_rule)
    if body.rule_type == RuleType.DATA:
        try:
            _sync_data_sharing(session, integrity_link_id, integrity_link)
        except (GeoServerAclError, ConsoleServiceError) as e:
            logger.error(
                "GeoServer sync failed while creating rule for IntegrityLink %s: %s",
                integrity_link_id,
                e,
            )
            session.rollback()
            raise HTTPException(status_code=500, detail="i18nerror.sync.geoserver")
    session.commit()
    _sync_metadata_sharing(session, integrity_link_id, integrity_link)
    return new_rule


@router.delete(
    "/{integrity_link_id}/rules/{rule_id}",
    status_code=204,
    summary="Delete a rule from an IntegrityLink",
)
def delete_integrity_link_rule(
    session: DatafeederSessionDep,
    georchestra_context: GeorchestraContextDep,
    integrity_link_id: str,
    group_ids: GroupIdsDep,
    rule_id: int,
) -> Response:
    """Delete a rule from a given IntegrityLink."""
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, georchestra_context, session, group_ids
    )

    rule = session.get(IntegrityLinkRule, rule_id)
    if not rule or rule.integrity_link_id != UUID(integrity_link_id):
        raise HTTPException(status_code=404, detail="Rule not found")

    rule_type = rule.rule_type
    session.delete(rule)
    session.flush()
    if rule_type == RuleType.DATA:
        try:
            _sync_data_sharing(session, integrity_link_id, integrity_link)
        except (GeoServerAclError, ConsoleServiceError) as e:
            logger.error(
                "GeoServer sync failed while deleting rule for IntegrityLink %s: %s",
                integrity_link_id,
                e,
            )
            session.rollback()
            raise HTTPException(status_code=500, detail="i18nerror.sync.geoserver")
    session.commit()
    _sync_metadata_sharing(session, integrity_link_id, integrity_link)
    return Response(status_code=204)


@router.put(
    "/{integrity_link_id}/publish-gn",
    response_model=IntegrityLinkResponse,
    summary="Publish or unpublish an IntegrityLink",
    description="Toggle the publication status of an IntegrityLink for Geonetwork",
)
def toggle_publish_gn_integrity_link(
    session: DatafeederSessionDep,
    georchestra_context: GeorchestraContextDep,
    integrity_link_id: str,
    publish: bool = Query(description="Set to true to publish, false to unpublish"),
) -> IntegrityLinkResponse:
    """Publish or unpublish an IntegrityLink metadata in GeoNetwork."""
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Verify that the IntegrityLink has metadata
    if not integrity_link.metadata_id:
        raise HTTPException(
            status_code=400,
            detail="IntegrityLink has no associated metadata to publish/unpublish",
        )

    # Create MetadataService instance
    settings = get_settings()
    metadata_service = MetadataService(
        gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
        datadir_path=settings.DATADIR_PATH,
        credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
        verify_tls=False,
    )

    # Publish or unpublish the metadata record
    try:
        metadata_service.toggle_publish_metadata_record(integrity_link.metadata_id, publish)
        action = "Published" if publish else "Unpublished"
        logger.info(
            f"{action} metadata {integrity_link.metadata_id} for IntegrityLink {integrity_link_id}"
        )

        # Update the gn_is_published status in database
        integrity_link.gn_is_published = publish
        session.add(integrity_link)
        session.commit()
        session.refresh(integrity_link)

    except Exception as e:
        logger.error(
            f"Failed to {'publish' if publish else 'unpublish'} metadata for IntegrityLink {integrity_link_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="i18nerror.publish.geonetwork",
        )

    return IntegrityLinkResponse.model_validate(integrity_link)


@router.delete(
    "/{integrity_link_id}/schedule",
    status_code=204,
    summary="Disable the recurrence schedule for a dataset",
    description="Clears the recurrence schedule and cancel any running or queued associated Airflow DAGs.",
)
def delete_integrity_link_schedule(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: str,
    group_ids: GroupIdsDep,
) -> Response:
    """Disable the recurrence schedule for a dataset."""
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, geo_ctx, session, group_ids
    )

    if not clear_schedule(integrity_link):
        return Response(status_code=204)

    session.commit()

    return Response(status_code=204)


@router.delete(
    "/{integrity_link_id}",
    status_code=204,
    summary="Delete a dataset and all associated resources",
    description=(
        "Deletes the dataset and triggers cleanup of: Airflow DAG (if scheduled), "
        "GeoServer layer, data tables, GeoNetwork record, and the IntegrityLink row. "
        "DAG deletion is the only blocking step — failure returns HTTP 500. "
        "All other steps are best-effort."
    ),
)
def delete_integrity_link(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: str,
    group_ids: GroupIdsDep,
) -> Response:
    """Delete a dataset and all associated resources."""
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, geo_ctx, session, group_ids
    )

    settings = get_settings()
    geoserver_service = GeoServerService(
        base_url=settings.GEOSERVER_INTERNAL_URL,
        username=settings.GEOSERVER_USER,
        password=settings.GEOSERVER_PASSWORD,
        public_url=settings.DATA_PUBLIC_URL,
    )
    metadata_service = MetadataService(
        gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
        datadir_path=settings.DATADIR_PATH,
        credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
        gn_sync_mode=settings.GN_SYNC_MODE,
        verify_tls=False,
    )
    deletion_service = DatasetDeletionService(
        geoserver_service=geoserver_service,
        metadata_service=metadata_service,
    )

    try:
        deletion_service.delete_dataset(integrity_link, session)
    except Exception as e:
        logger.error(
            f"Failed to delete dataset {integrity_link_id}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {e}")

    return Response(status_code=204)


@router.put(
    "/{integrity_link_id}/publish-gs",
    response_model=IntegrityLinkGsPublishResponse,
    summary="Publish or unpublish an IntegrityLink on GeoServer",
    description=(
        "Toggle the publication status of an IntegrityLink layer on GeoServer (ACL READ rule). "
        "**Note:** restricting access (unpublish) only has effect if GeoServer does not have a "
        "global rule granting read access to everyone (e.g. `*.*.r = *`). "
        "If such a global rule exists, removing the layer-level rule will not prevent public access."
    ),
)
def toggle_publish_gs_integrity_link(
    session: DatafeederSessionDep,
    georchestra_context: GeorchestraContextDep,
    group_ids: GroupIdsDep,
    geoserver_service: GeoServerServiceDep,
    integrity_link_id: str,
    publish: bool = Query(description="Set to true to publish, false to unpublish"),
) -> IntegrityLinkGsPublishResponse:
    """Publish or unpublish an IntegrityLink layer on GeoServer by managing its ACL read rule."""
    integrity_link, _ = load_authorized_integrity_link(
        integrity_link_id,
        AccessLevel.OWNER_ONLY,
        georchestra_context,
        session,
        group_ids,
    )
    if not integrity_link.final_table_name:
        raise HTTPException(
            status_code=400,
            detail="IntegrityLink has no associated layer to publish/unpublish",
        )

    acl_layer_name = GeoServerService.make_acl_layer_name(
        integrity_link.integrity_organization, integrity_link.final_table_name
    )
    gs_read_roles: list[str] | None = None
    try:
        if publish:
            session.add(
                IntegrityLinkRule(
                    integrity_link_id=UUID(integrity_link_id),
                    rule_type=RuleType.DATA,
                    rule_value=RuleValue.READ,
                    group_or_role=GROUP_OR_ROLE_EVERYONE,
                )
            )
            _sync_data_sharing(session, integrity_link_id, integrity_link, geoserver_service)
        else:
            everyone_rules = session.exec(
                select(IntegrityLinkRule).where(
                    IntegrityLinkRule.integrity_link_id == UUID(integrity_link_id),
                    IntegrityLinkRule.rule_type == RuleType.DATA,
                    IntegrityLinkRule.rule_value == RuleValue.READ,
                    IntegrityLinkRule.group_or_role == GROUP_OR_ROLE_EVERYONE,
                )
            ).all()
            for rule in everyone_rules:
                session.delete(rule)
            session.flush()  # make deletions visible before the sync query
            _sync_data_sharing(session, integrity_link_id, integrity_link, geoserver_service)

        gs_read_roles = geoserver_service.acl_layer_get(
            layer_name=acl_layer_name,
            access_type=AclAccessType.READ,
        )
        action = "Published" if publish else "Unpublished"
        logger.info(
            f"{action} GeoServer layer {integrity_link.integrity_organization}/{integrity_link.final_table_name} "
            f"for IntegrityLink {integrity_link_id}"
        )

        integrity_link.gs_is_published = publish
        session.add(integrity_link)
        session.commit()
        session.refresh(integrity_link)

    except Exception as e:
        session.rollback()
        response_body: str | None = None
        if isinstance(e, GeoServerAclError):
            response_body = e.body
        logger.error(
            f"Failed to {'publish' if publish else 'unpublish'} GeoServer layer for IntegrityLink {integrity_link_id}: {e}"
            + (f" — GeoServer response: {response_body}" if response_body else ""),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="i18nerror.publish.geoserver",
        )

    response = IntegrityLinkGsPublishResponse.model_validate(integrity_link)
    response.gs_read_roles = gs_read_roles
    response.rules = list(
        session.exec(
            select(IntegrityLinkRule).where(
                IntegrityLinkRule.integrity_link_id == UUID(integrity_link_id)
            )
        ).all()
    )
    return response


@router.patch(
    "/{integrity_link_id}/schedule",
    response_model=IntegrityLinkResponse,
    summary="Update recurrence schedule",
    description="Set or clear the recurrence schedule for an IntegrityLink.",
)
def update_schedule(
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: str,
    group_ids: GroupIdsDep,
    preset: RecurrencePreset | None = Body(None, embed=True),
) -> IntegrityLinkResponse:
    """Set or clear the recurrence schedule for an IntegrityLink."""
    integrity_link, effective = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, geo_ctx, session, group_ids
    )

    if preset is not None:
        integrity_link.schedule = preset.cron
        integrity_link.schedule_enabled = True
    else:
        clear_schedule(integrity_link)

    session.commit()
    session.refresh(integrity_link)

    resolved_preset = (
        RecurrencePreset.from_cron(integrity_link.schedule) if integrity_link.schedule else None
    )
    return IntegrityLinkResponse.model_validate(integrity_link).model_copy(
        update={"access_level": effective.value, "preset_id": resolved_preset}
    )
