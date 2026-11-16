"""Authentication with the geOrchestra security headers, for direct calls to the backends.

Behind the gateway, GeoServer and GeoNetwork trust the ``sec-*`` headers it sends. Without an
LDAP, the gateway can no longer check HTTP Basic credentials: datafeeder then calls the
backends directly on the internal network (``GEOSERVER_INTERNAL_URL`` /
``GEONETWORK_INTERNAL_URL`` pointing at them, not at the gateway) with the headers of a
technical account (``GEOSERVER_AUTH=headers`` / ``GEONETWORK_AUTH=headers``).

The backends must not be reachable from outside: anyone reaching them can send these headers.
GeoNetwork resolves the user in its accounts source (Keycloak), so the account must exist there.
"""

from collections.abc import Generator
from typing import TYPE_CHECKING

import httpx
from requests import PreparedRequest
from requests.auth import AuthBase

if TYPE_CHECKING:
    from src.core.config import Settings


class GeorchestraHeadersAuth(httpx.Auth, AuthBase):
    """Adds ``sec-proxy``, ``sec-username`` and ``sec-roles``; works with httpx and requests."""

    def __init__(self, username: str, roles: str, organization: str = ""):
        self.headers = {
            "sec-proxy": "true",
            "sec-username": username,
            # geOrchestra separates roles with ";"
            "sec-roles": ";".join(
                r.strip() for r in roles.replace(",", ";").split(";") if r.strip()
            ),
        }
        if organization:
            self.headers["sec-org"] = organization

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers.update(self.headers)
        yield request

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        r.headers.update(self.headers)
        return r


def geoserver_auth(settings: "Settings") -> GeorchestraHeadersAuth | None:
    """Authentication of the GeoServer calls replacing HTTP Basic, per ``GEOSERVER_AUTH``."""
    if settings.GEOSERVER_AUTH == "headers":
        return GeorchestraHeadersAuth(settings.GEOSERVER_USER, settings.SEC_HEADERS_ROLES)
    return None


def geonetwork_headers_auth(settings: "Settings") -> GeorchestraHeadersAuth:
    """Authentication of the GeoNetwork calls for ``GEONETWORK_AUTH=headers``."""
    return GeorchestraHeadersAuth(settings.GEONETWORK_USERNAME, settings.SEC_HEADERS_ROLES)
