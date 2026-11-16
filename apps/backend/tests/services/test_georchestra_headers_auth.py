from unittest.mock import MagicMock

import httpx
import requests

from src.services.georchestra_headers_auth import (
    GeorchestraHeadersAuth,
    geonetwork_headers_auth,
    geoserver_auth,
)
from src.services.geoserver import GeoServerService

EXPECTED = {
    "sec-proxy": "true",
    "sec-username": "svc",
    "sec-roles": "ROLE_ADMINISTRATOR;ROLE_GN_ADMIN",
}


def test_httpx_request_gets_the_headers() -> None:
    auth = GeorchestraHeadersAuth("svc", "ROLE_ADMINISTRATOR, ROLE_GN_ADMIN")
    request = httpx.Request("GET", "http://geoserver:8080/geoserver/rest")

    sent = next(auth.auth_flow(request))

    assert {k: sent.headers[k] for k in EXPECTED} == EXPECTED


def test_requests_request_gets_the_headers() -> None:
    auth = GeorchestraHeadersAuth("svc", "ROLE_ADMINISTRATOR;ROLE_GN_ADMIN", organization="PSC")
    prepared = requests.Request("GET", "http://geonetwork:8080/geonetwork").prepare()

    prepared = auth(prepared)

    assert {k: prepared.headers[k] for k in EXPECTED} == EXPECTED
    assert prepared.headers["sec-org"] == "PSC"


def test_auth_selection_from_settings() -> None:
    settings = MagicMock(
        GEOSERVER_AUTH="basic",
        GEOSERVER_USER="svc",
        GEONETWORK_USERNAME="gn",
        SEC_HEADERS_ROLES="ROLE_ADMINISTRATOR",
    )
    assert geoserver_auth(settings) is None

    settings.GEOSERVER_AUTH = "headers"
    auth = geoserver_auth(settings)
    assert auth is not None and auth.headers["sec-username"] == "svc"
    assert geonetwork_headers_auth(settings).headers["sec-username"] == "gn"


def test_geoserver_service_uses_the_auth_for_rest_calls() -> None:
    auth = GeorchestraHeadersAuth("svc", "ROLE_ADMINISTRATOR")

    service = GeoServerService(
        "http://geoserver:8080/geoserver", "svc", "", "http://public", auth=auth
    )

    assert service.geoserver.rest_service.rest_client.auth is auth
