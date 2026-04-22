from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from uuid import UUID

import jwt
from fastapi import HTTPException
from sqlalchemy import case, exists, literal
from sqlalchemy.sql.expression import Label
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


def build_access_expr(
    username: str,
    group_ids: list[str],
    is_admin: bool,
) -> Label[str | None]:
    """Build a SQL expression that computes the effective access level.

    Returns a labelled column expression evaluating to one of the
    :class:`EffectiveAccess` values (``ADMIN``, ``OWNER``, ``WRITE``,
    ``READ``), or ``None`` when the user has no access.

    ``group_ids`` is the set of identifiers (a single org UUID in ORG mode, or
    one entry per user role in ROLE mode) that must match
    ``IntegrityLinkRule.group_or_role``. A single WRITE/READ pair of conditions
    is emitted regardless of list length, so WRITE from any group takes
    precedence over READ from any other group.

    Callers that list multiple rows should combine this with a WHERE clause
    that excludes ``None``-access rows; single-row callers can map ``None``
    to a 403.

    The expression references ``IntegrityLink`` columns and correlated
    ``IntegrityLinkRule`` subqueries, so it must be used inside a
    ``SELECT … FROM integrity_link`` context.
    """
    if is_admin:
        return literal(EffectiveAccess.ADMIN.value).label("access_level")  # type: ignore[return-value]

    conditions: list[tuple[Any, str]] = [
        (IntegrityLink.integrity_owner == username, EffectiveAccess.OWNER.value),  # type: ignore[arg-type]
    ]

    if group_ids:
        write_rule_exists = exists(
            select(IntegrityLinkRule.id).where(
                IntegrityLinkRule.integrity_link_id == IntegrityLink.id,
                IntegrityLinkRule.rule_type == RuleType.METADATA,
                IntegrityLinkRule.group_or_role.in_(group_ids),  # type: ignore[attr-defined]
                IntegrityLinkRule.rule_value == RuleValue.WRITE,
            )
        )
        read_rule_exists = exists(
            select(IntegrityLinkRule.id).where(
                IntegrityLinkRule.integrity_link_id == IntegrityLink.id,
                IntegrityLinkRule.rule_type == RuleType.METADATA,
                IntegrityLinkRule.group_or_role.in_(group_ids),  # type: ignore[attr-defined]
            )
        )
        conditions.append((write_rule_exists, EffectiveAccess.WRITE.value))
        conditions.append((read_rule_exists, EffectiveAccess.READ.value))

    return case(*conditions, else_=None).label("access_level")


def compute_effective_access(
    integrity_link: IntegrityLink,
    geo_ctx: GeorchestraContext,
    session: Session,
    group_ids: list[str],
) -> EffectiveAccess | None:
    """Compute the effective access level for a user on a dataset.

    Uses the same SQL CASE expression as the list endpoint
    (via :func:`build_access_expr`) so the permission logic is defined once.

    Returns the highest applicable access level, or None if no access.

    Args:
        integrity_link: The dataset to check access for
        geo_ctx: The user's geOrchestra security context
        session: Database session for querying rules
        group_ids: Identifiers to match against ``IntegrityLinkRule.group_or_role``
            (org UUID in ORG mode, role UUIDs in ROLE mode). Empty list disables
            group-based access.

    Returns:
        EffectiveAccess level or None if no access
    """
    access_expr = build_access_expr(geo_ctx.username, group_ids, geo_ctx.is_administrator())
    result = session.exec(
        select(access_expr)
        .select_from(IntegrityLink)  # type: ignore[arg-type]
        .where(IntegrityLink.id == integrity_link.id)
    ).first()

    if result is None:
        return None

    return EffectiveAccess(result)


def load_authorized_integrity_link(
    integrity_link_id: str,
    required_level: AccessLevel,
    geo_ctx: GeorchestraContext,
    session: Session,
    group_ids: list[str],
) -> tuple[IntegrityLink, EffectiveAccess]:
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
        group_ids: Identifiers to match against ``IntegrityLinkRule.group_or_role``
            (org UUID in ORG mode, role UUIDs in ROLE mode). Empty list disables
            group-based access.

    Returns:
        Tuple of (IntegrityLink, EffectiveAccess) — the entity and the caller's access level

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

    effective = compute_effective_access(integrity_link, geo_ctx, session, group_ids)

    if effective is None:
        raise HTTPException(
            status_code=403, detail="You do not have permission to access this dataset"
        )

    # Admin and owner always pass
    if effective in (EffectiveAccess.ADMIN, EffectiveAccess.OWNER):
        return integrity_link, effective

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
    return integrity_link, effective
