from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from sqlmodel import select

from src.api.deps import DatakernSessionDep, GeorchestraContextDep, OrgIdDep
from src.core.security import (
    AccessLevel,
    compute_effective_access,
    load_authorized_integrity_link,
)
from src.models.data_import import IntegrityLinkResponse
from src.models.integrity_link_rule import IntegrityLinkRule, UpsertRuleRequest

router = APIRouter(prefix="/ingestion/integrity-link", tags=["Ingestion"])


@router.get(
    "/{integrity_link_id}",
    response_model=IntegrityLinkResponse,
    summary="Get IntegrityLink by ID",
    description="Retrieve an IntegrityLink entity. The integrity_transformation field is excluded by default.",
)
def get_integrity_link(
    session: DatakernSessionDep,
    geo_ctx: GeorchestraContextDep,
    integrity_link_id: str,
    org_id: OrgIdDep,
    include_transformation: bool = Query(
        False,
        description="Include the integrity_transformation field in the response",
    ),
) -> IntegrityLinkResponse:
    """Get an IntegrityLink entity by its ID."""
    integrity_link = load_authorized_integrity_link(
        integrity_link_id, AccessLevel.METADATA_WRITE, geo_ctx, session, org_id
    )

    response = IntegrityLinkResponse.model_validate(integrity_link)

    effective = compute_effective_access(integrity_link, geo_ctx, session, org_id)
    response.access_level = effective.value if effective else None

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
    session: DatakernSessionDep,
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
    session: DatakernSessionDep,
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
    session: DatakernSessionDep,
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
