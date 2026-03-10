from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from sqlmodel import select

from src.api.deps import DatafeederSessionDep, GeorchestraContextDep, OrgIdDep
from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.security import (
    AccessLevel,
    load_authorized_integrity_link,
)
from src.models.data_import import IntegrityLinkResponse
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import IntegrityLinkRule, UpsertRuleRequest
from src.services.metadata_service import MetadataService

logger = get_logger()

router = APIRouter(prefix="/ingestion/integrity-link", tags=["Ingestion"])


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
    org_id: OrgIdDep,
    include_transformation: bool = Query(
        False,
        description="Include the integrity_transformation field in the response",
    ),
) -> IntegrityLinkResponse:
    """Get an IntegrityLink entity by its ID."""
    integrity_link, effective = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.METADATA_WRITE, geo_ctx, session, org_id
    )

    response = IntegrityLinkResponse.model_validate(integrity_link)
    response.access_level = effective.value

    if not include_transformation:
        response.integrity_transformation = None

    return response


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
    org_id: OrgIdDep,
) -> list[IntegrityLinkRule]:
    """List all rules for a given IntegrityLink."""
    load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, georchestra_context, session, org_id
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
    org_id: OrgIdDep,
    body: UpsertRuleRequest,
) -> IntegrityLinkRule:
    """Create or update a rule for a given IntegrityLink."""
    load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, georchestra_context, session, org_id
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
        session.commit()
        session.refresh(existing_rule)
        return existing_rule

    new_rule = IntegrityLinkRule(
        integrity_link_id=UUID(integrity_link_id),
        group_or_role=body.group_or_role,
        rule_type=body.rule_type,
        rule_value=body.rule_value,
    )
    session.add(new_rule)
    session.commit()
    session.refresh(new_rule)
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
    org_id: OrgIdDep,
    rule_id: int,
) -> Response:
    """Delete a rule from a given IntegrityLink."""
    load_authorized_integrity_link(
        integrity_link_id, AccessLevel.OWNER_ONLY, georchestra_context, session, org_id
    )

    rule = session.get(IntegrityLinkRule, rule_id)
    if not rule or rule.integrity_link_id != UUID(integrity_link_id):
        raise HTTPException(status_code=404, detail="Rule not found")

    session.delete(rule)
    session.commit()
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
        gn_api_url=f"{settings.GEONETWORK_URL}/srv/api",
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
