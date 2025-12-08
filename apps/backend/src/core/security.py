from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from src.core.config import get_settings

ALGORITHM = "HS256"


def create_access_token(subject: str | Any, expires_delta: timedelta) -> str:
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, get_settings().SECRET_KEY, algorithm=ALGORITHM)  # type: ignore[arg-type]
    return encoded_jwt
