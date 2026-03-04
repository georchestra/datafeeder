from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID

import jwt
from fastapi import HTTPException
from sqlmodel import Session, select

from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import IntegrityLinkRule, RuleType, RuleValue
from src.services.georchestra import GeorchestraContext

logger = get_logger()

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, get_settings().SECRET_KEY, algorithm=ALGORITHM)  # type: ignore[arg-type]
    return encoded_jwt


class AccessLevel(str, Enum):
    """Required access level for permission checks.

    Hierarchy (from most permissive to most restrictive):
    - METADATA_READ: User's group has at least METADATA READ rule
    - METADATA_WRITE: User's group has METADATA WRITE rule (implies READ)
    - OWNER_ONLY: Only dataset owner or administrator
    """

    METADATA_READ = "METADATA_READ"
    METADATA_WRITE = "METADATA_WRITE"
    OWNER_ONLY = "OWNER_ONLY"


class EffectiveAccess(str, Enum):
    """Effective access level computed for a user on a dataset."""

    ADMIN = "ADMIN"
    OWNER = "OWNER"
    WRITE = "WRITE"
    READ = "READ"


def compute_effective_access(
    integrity_link: IntegrityLink,
    geo_ctx: GeorchestraContext,
    session: Session,
    org_id: str | None,
) -> EffectiveAccess | None:
    """Compute the effective access level for a user on a dataset.

    Returns the highest applicable access level, or None if no access.

    Args:
        integrity_link: The dataset to check access for
        geo_ctx: The user's geOrchestra security context
        session: Database session for querying rules
        org_id: Pre-resolved console UUID for the user's organisation (or None)

    Returns:
        EffectiveAccess level or None if no access
    """
    if geo_ctx.is_administrator():
        return EffectiveAccess.ADMIN

    if integrity_link.integrity_owner == geo_ctx.username:
        return EffectiveAccess.OWNER

    if org_id is None:
        return None

    # Query for METADATA rules matching the user's organization
    statement = select(IntegrityLinkRule).where(
        IntegrityLinkRule.integrity_link_id == integrity_link.id,
        IntegrityLinkRule.rule_type == RuleType.METADATA,
        IntegrityLinkRule.group_or_role == org_id,
    )
    rules = session.exec(statement).all()

    if not rules:
        return None

    # Check for WRITE (highest group-based access)
    for rule in rules:
        if rule.rule_value == RuleValue.WRITE:
            return EffectiveAccess.WRITE

    # Otherwise must be READ
    return EffectiveAccess.READ


def load_authorized_integrity_link(
    integrity_link_id: str,
    required_level: AccessLevel,
    geo_ctx: GeorchestraContext,
    session: Session,
    org_id: str | None,
) -> IntegrityLink:
    """Load an IntegrityLink and verify the user has the required permission.

    Loads the IntegrityLink by ID and checks that the user's effective access
    level meets the required level. Raises HTTP exceptions on failure.

    Permission hierarchy:
    - Admin and owner always pass any check
    - METADATA_WRITE satisfies METADATA_READ (WRITE implies READ)
    - OWNER_ONLY requires owner or admin status

    Args:
        integrity_link_id: UUID string of the dataset
        required_level: Minimum access level required
        geo_ctx: The user's geOrchestra security context
        session: Database session
        org_id: Pre-resolved console UUID for the user's organisation (or None)

    Returns:
        The loaded IntegrityLink entity

    Raises:
        HTTPException 404: If IntegrityLink not found
        HTTPException 403: If user lacks the required access level
    """
    integrity_link_id_as_uuid = None

    try:
        integrity_link_id_as_uuid = UUID(integrity_link_id)
    except ValueError:
        raise HTTPException(
            status_code=422, detail="Invalid integrity_link_id format; expected a valid UUID"
        )

    integrity_link = session.get(IntegrityLink, integrity_link_id_as_uuid)
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    effective = compute_effective_access(integrity_link, geo_ctx, session, org_id)

    if effective is None:
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this dataset"
        )

    # Admin and owner always pass
    if effective in (EffectiveAccess.ADMIN, EffectiveAccess.OWNER):
        return integrity_link

    # For OWNER_ONLY, only admin/owner pass (already handled above)
    if required_level == AccessLevel.OWNER_ONLY:
        raise HTTPException(
            status_code=403,
            detail="Only the dataset owner or an administrator can perform this action",
        )

    # For METADATA_WRITE, need at least WRITE
    if required_level == AccessLevel.METADATA_WRITE and effective == EffectiveAccess.READ:
        raise HTTPException(
            status_code=403, detail="You need METADATA WRITE permission to perform this action"
        )

    # METADATA_READ: READ or WRITE both pass
    return integrity_link
