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
from src.core.db import data_engine, datakern_engine
from src.models import TokenPayload, User
from src.services.console_service import ConsoleService
from src.services.georchestra import GeorchestraContext, get_georchestra_context

reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{get_settings().API_V1_STR}/login/access-token")


def get_datakern_db() -> Generator[Session, None, None]:
    with Session(datakern_engine) as session:
        yield session


def get_data_db() -> Generator[Session, None, None]:
    with Session(data_engine) as session:
        yield session


DatakernSessionDep = Annotated[Session, Depends(get_datakern_db)]
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


OrgIdDep = Annotated[str | None, Depends(get_org_id)]


def get_current_user(session: DatakernSessionDep, token: TokenDep) -> User:
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
