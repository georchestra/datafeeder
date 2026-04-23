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

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{get_settings().API_V1_STR}/login/access-token")


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

    service = ConsoleService(get_settings().CONSOLE_URL)
    org = service.get_organization(geo_ctx.organization)

    return str(org["id"]) if org and "id" in org else None


def get_group_ids(geo_ctx: GeorchestraContextDep) -> list[str]:
    """Resolve the identifiers used to match ``IntegrityLinkRule.group_or_role``.

    In ORG mode the list contains the user's org console UUID (at most one entry);
    in ROLE mode it contains the UUIDs of every role the user holds. An empty list
    means the user has no group-based access — only the owner/admin paths apply.

    Performs one Console round-trip per request; FastAPI deduplicates the dependency.
    Fail-closed on Console errors: a warning is logged and an empty list is returned,
    so owner/admin paths keep working while group-based access is denied until the
    Console is reachable.
    """
    settings = get_settings()
    if settings.GN_SYNC_MODE == "ROLE":
        if not geo_ctx.roles:
            return []
        try:
            all_roles = ConsoleService(settings.CONSOLE_URL).get_all_roles()
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
            if role.get("id") and role.get("name") and role["name"].upper() in geo_ctx.roles
        ]

    org_id = get_org_id(geo_ctx)
    return [org_id] if org_id else []


GroupIdsDep = Annotated[list[str], Depends(get_group_ids)]


def get_geoserver_service() -> GeoServerService:
    settings = get_settings()
    return GeoServerService(
        base_url=settings.GEOSERVER_URL,
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
