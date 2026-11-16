"""Keycloak service-account (client credentials) access tokens.

Used to call the Keycloak admin API (``KeycloakDirectoryService``) and, with
``GEONETWORK_AUTH=keycloak``, GeoNetwork in its ``jwt-headers`` security mode (bearer token
instead of Basic auth).
"""

import threading
import time
from collections.abc import Generator
from functools import lru_cache

import httpx
import requests
from requests.auth import AuthBase

from src.core.config import Settings
from src.core.logging import get_logger

logger = get_logger()

# Renew the token this many seconds before it expires
EXPIRY_MARGIN_SECONDS = 30


class KeycloakTokenError(Exception):
    """Raised when no access token can be obtained from Keycloak."""


class KeycloakTokenProvider:
    """Fetches and caches a client-credentials access token (thread-safe)."""

    def __init__(self, base_url: str, realm: str, client_id: str, client_secret: str):
        self.token_url = f"{base_url.rstrip('/')}/realms/{realm}/protocol/openid-connect/token"
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        with self._lock:
            if self._token is None or time.monotonic() >= self._expires_at:
                self._token, self._expires_at = self._fetch_token()
            return self._token

    def invalidate(self) -> None:
        with self._lock:
            self._token = None

    def _fetch_token(self) -> tuple[str, float]:
        try:
            response = httpx.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=5.0,
            )
            response.raise_for_status()
            payload = response.json()
            token = str(payload["access_token"])
            expires_in = float(payload.get("expires_in", 60))
        except Exception as exc:
            raise KeycloakTokenError(
                f"Failed to get an access token from {self.token_url}: {exc}"
            ) from exc
        logger.debug("Got Keycloak access token for client '%s'", self.client_id)
        return token, time.monotonic() + max(expires_in - EXPIRY_MARGIN_SECONDS, 0)


@lru_cache
def _get_token_provider(
    base_url: str, realm: str, client_id: str, client_secret: str
) -> KeycloakTokenProvider:
    return KeycloakTokenProvider(base_url, realm, client_id, client_secret)


def get_token_provider(settings: Settings) -> KeycloakTokenProvider:
    """Process-wide token provider for the configured service-account client."""
    return _get_token_provider(
        settings.KEYCLOAK_INTERNAL_URL,
        settings.KEYCLOAK_REALM,
        settings.KEYCLOAK_CLIENT_ID,
        settings.KEYCLOAK_CLIENT_SECRET,
    )


class KeycloakHttpxAuth(httpx.Auth):
    """httpx auth adding ``Authorization: Bearer <token>``, retried once on 401."""

    def __init__(self, provider: KeycloakTokenProvider):
        self.provider = provider

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self.provider.get_token()}"
        response = yield request
        if response.status_code == 401:
            self.provider.invalidate()
            request.headers["Authorization"] = f"Bearer {self.provider.get_token()}"
            yield request


class KeycloakRequestsAuth(AuthBase):
    """requests auth adding ``Authorization: Bearer <token>`` (e.g. for GnApi credentials)."""

    def __init__(self, provider: KeycloakTokenProvider):
        self.provider = provider

    def __call__(self, request: requests.PreparedRequest) -> requests.PreparedRequest:
        request.headers["Authorization"] = f"Bearer {self.provider.get_token()}"
        return request
