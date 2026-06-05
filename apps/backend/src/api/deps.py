import re
from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import Session

from src.core import security
from src.core.config import get_settings
from src.core.db import data_engine, datafeeder_engine
from src.core.logging import get_logger
from src.models import TokenPayload, User
from src.services.console_service import ConsoleService, ConsoleServiceError
from src.services.georchestra import GeorchestraContext, get_georchestra_context
from src.services.geoserver import GeoServerService

logger = get_logger()

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/login/access-token")


def get_datafeeder_db() -> Generator[Session, None, None]:
    with Session(datafeeder_engine) as session:
        yield session


def get_data_db() -> Generator[Session, None, None]:
    with Session(data_engine) as session:
        yield session


DatafeederSessionDep = Annotated[Session, Depends(get_datafeeder_db)]
DataSessionDep = Annotated[Session, Depends(get_data_db)]
TokenDep = Annotated[str, Depends(reusable_oauth2)]
GeorchestraContextDep = Annotated[GeorchestraContext, Depends(get_georchestra_context)]


def get_org_id(geo_ctx: GeorchestraContextDep) -> str | None:
    """Resolve the current user's org shortName to its console UUID once per request.

    FastAPI deduplicates dependencies — geo_ctx is shared with the route handler.
    Returns the UUID string from the console, or None if the org is not found or
    if the console is unreachable (user treated as having no org-based access).
    """
    if not geo_ctx.organization:
        return None

    service = ConsoleService(get_settings().CONSOLE_INTERNAL_URL)
    org = service.get_organization(geo_ctx.organization)

    return str(org["id"]) if org and "id" in org else None


def _compile_metadata_filter(raw: str) -> re.Pattern[str] | None:
    """Compile ``METADATA_GROUPS_LABEL_FILTER_REGEX``; ``None`` when unset.

    Raises :class:`re.error` on invalid regex so callers can fail closed.
    """
    if not raw:
        return None
    return re.compile(raw)


def _matches_metadata_filter(name: str, pattern: re.Pattern[str] | None) -> bool:
    return pattern is None or pattern.search(name) is not None


def get_group_ids(geo_ctx: GeorchestraContextDep) -> list[str]:
    """Resolve the identifiers used to match ``IntegrityLinkRule.group_or_role``.

    In ORG mode the list contains the user's org console UUID (at most one entry);
    in ROLE mode it contains the UUIDs of every role the user holds. An empty list
    means the user has no group-based access — only the owner/admin paths apply.

    ``METADATA_GROUPS_LABEL_FILTER_REGEX`` is applied here as a security boundary:
    only groups whose name matches the regex can grant access, even if a rule
    exists in the database pointing at an out-of-filter group. This prevents
    rules created outside the UI (direct API calls, seeded data, or rules whose
    matching filter was tightened afterwards) from bypassing the filter.

    Performs one Console round-trip per request; FastAPI deduplicates the dependency.
    Fail-closed on Console errors and on an invalid regex: a warning/error is logged
    and an empty list is returned, so owner/admin paths keep working while
    group-based access is denied until the Console is reachable or the config is fixed.
    """
    settings = get_settings()

    try:
        pattern = _compile_metadata_filter(settings.METADATA_GROUPS_LABEL_FILTER_REGEX)
    except re.error as exc:
        logger.error(
            "Invalid METADATA_GROUPS_LABEL_FILTER_REGEX %r; denying group access: %s",
            settings.METADATA_GROUPS_LABEL_FILTER_REGEX,
            exc,
        )
        return []

    if settings.GN_SYNC_MODE == "ROLE":
        if not geo_ctx.roles:
            return []
        # PERF: one Console call per request; acceptable at UI scale. If this
        # becomes hot, promote ConsoleService to a request-scoped FastAPI dep
        # and memoize get_all_roles on the instance so rule-sync paths share it.
        try:
            all_roles = ConsoleService(settings.CONSOLE_INTERNAL_URL).get_all_roles()
        except ConsoleServiceError as exc:
            logger.warning(
                "Console unreachable while resolving role UUIDs; "
                "group-based access denied for user '%s': %s",
                geo_ctx.username,
                exc,
            )
            return []
        return [
            str(role["id"])
            for role in all_roles
            if role.get("id")
            and role.get("name")
            and role["name"].upper() in geo_ctx.roles
            and _matches_metadata_filter(str(role["name"]), pattern)
        ]

    if not geo_ctx.organization:
        return []
    org = ConsoleService(settings.CONSOLE_INTERNAL_URL).get_organization(geo_ctx.organization)
    if not org or "id" not in org:
        return []
    if not _matches_metadata_filter(str(org.get("name", "")), pattern):
        return []
    return [str(org["id"])]


GroupIdsDep = Annotated[list[str], Depends(get_group_ids)]


def get_geoserver_service() -> GeoServerService:
    settings = get_settings()
    return GeoServerService(
        base_url=settings.GEOSERVER_INTERNAL_URL,
        username=settings.GEOSERVER_USER,
        password=settings.GEOSERVER_PASSWORD,
        public_url=settings.DATA_PUBLIC_URL,
    )


GeoServerServiceDep = Annotated[GeoServerService, Depends(get_geoserver_service)]


def get_current_user(session: DatafeederSessionDep, token: TokenDep) -> User:
    try:
        payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=[security.ALGORITHM])  # type: ignore[arg-type]
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.get(User, token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_current_active_superuser(current_user: CurrentUserDep) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return current_user
