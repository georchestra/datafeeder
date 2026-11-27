import hashlib
import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi import HTTPException

from src.api.routes import geonetwork
from src.api.routes.geonetwork import authorize_geonetwork_call, geonetwork_me
from src.core.security import AccessLevel
from src.services.georchestra import GeorchestraContext


async def proxy_geonetwork(path: str, request: Mock):
    """Call the route with dummy auth dependencies (authorization is tested separately)."""
    with patch("src.api.routes.geonetwork.authorize_geonetwork_call"):
        return await geonetwork.proxy_geonetwork(path, request, Mock(), Mock(), [])


class TestGeoNetworkProxy:
    """Test cases for GeoNetwork pass-through proxy."""

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings for GeoNetwork connection."""
        settings = Mock()
        settings.GEONETWORK_INTERNAL_URL = "http://geonetwork.example.com/geonetwork"
        settings.GEONETWORK_USERNAME = "test_user"
        settings.GEONETWORK_PASSWORD = "test_pass"
        return settings

    def _create_mock_request(
        self,
        method: str = "GET",
        query: str = "",
        headers: dict[str, str] | None = None,
        body: bytes = b"",
    ) -> Mock:
        """Create a mock FastAPI Request object."""
        request = Mock()
        request.method = method
        request.url = Mock()
        request.url.query = query
        request.headers = headers or {}
        request.body = AsyncMock(return_value=body)
        return request

    @pytest.mark.asyncio
    async def test_given_get_request_when_proxying_then_forwards_path_and_query(
        self, mock_settings: Mock
    ) -> None:
        """Given a GET request, when proxying, then forwards path and query params."""
        path = "srv/api/records/test-uuid"
        query = "format=xml&lang=en"
        request = self._create_mock_request(method="GET", query=query)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<xml>test</xml>"
        mock_response.headers = {"content-type": "application/xml"}

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.request.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                response = await proxy_geonetwork(path, request)

                # Verify correct URL with query string
                call_kwargs = mock_client.request.call_args.kwargs
                assert call_kwargs["method"] == "GET"
                expected_url = f"{mock_settings.GEONETWORK_INTERNAL_URL}/{path}?{query}"
                assert call_kwargs["url"] == expected_url

                # Verify response
                assert response.status_code == 200
                assert response.body == b"<xml>test</xml>"

    @pytest.mark.asyncio
    async def test_given_post_request_when_proxying_then_forwards_body(
        self, mock_settings: Mock
    ) -> None:
        """Given a POST request, when proxying, then forwards request body."""
        path = "srv/api/records"
        body = b'{"title": "Test Record"}'
        request = self._create_mock_request(
            method="POST", headers={"content-type": "application/json"}, body=body
        )

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": "new-uuid"}'
        mock_response.headers = {"content-type": "application/json"}

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.request.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                response = await proxy_geonetwork(path, request)

                # Verify body was forwarded
                call_kwargs = mock_client.request.call_args.kwargs
                assert call_kwargs["method"] == "POST"
                assert call_kwargs["content"] == body

                # Verify response preserves status
                assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_given_upstream_404_when_proxying_then_preserves_status(
        self, mock_settings: Mock
    ) -> None:
        """Given upstream returns 404, when proxying, then preserves status code."""
        path = "srv/api/records/nonexistent"
        request = self._create_mock_request(method="GET")

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.content = b"Not found"
        mock_response.headers = {"content-type": "text/plain"}

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.request.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                response = await proxy_geonetwork(path, request)

                # Proxy should preserve the 404 status
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_given_timeout_when_proxying_then_raises_504(self, mock_settings: Mock) -> None:
        """Given upstream timeout, when proxying, then raises 504 error."""
        path = "srv/api/records"
        request = self._create_mock_request(method="GET")

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.request.side_effect = httpx.TimeoutException("Timeout")
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with pytest.raises(HTTPException) as exc_info:
                    await proxy_geonetwork(path, request)

                assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_given_connection_error_when_proxying_then_raises_502(
        self, mock_settings: Mock
    ) -> None:
        """Given connection error, when proxying, then raises 502 error."""
        path = "srv/api/records"
        request = self._create_mock_request(method="GET")

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.request.side_effect = httpx.RequestError("Connection failed")
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with pytest.raises(HTTPException) as exc_info:
                    await proxy_geonetwork(path, request)

                assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_given_put_request_when_proxying_then_forwards_body(
        self, mock_settings: Mock
    ) -> None:
        """Given a PUT request, when proxying, then forwards request body."""
        path = "srv/api/records/test-uuid"
        body = b'{"title": "Updated Record"}'
        request = self._create_mock_request(
            method="PUT", headers={"content-type": "application/json"}, body=body
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"id": "test-uuid"}'
        mock_response.headers = {"content-type": "application/json"}

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.request.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                response = await proxy_geonetwork(path, request)

                # Verify body was forwarded
                call_kwargs = mock_client.request.call_args.kwargs
                assert call_kwargs["method"] == "PUT"
                assert call_kwargs["content"] == body
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_given_delete_request_when_proxying_then_forwards_correctly(
        self, mock_settings: Mock
    ) -> None:
        """Given a DELETE request, when proxying, then forwards correctly."""
        path = "srv/api/records/test-uuid"
        request = self._create_mock_request(method="DELETE")

        mock_response = Mock()
        mock_response.status_code = 204
        mock_response.content = b""
        mock_response.headers = {}

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.request.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                response = await proxy_geonetwork(path, request)

                # Verify method was forwarded
                call_kwargs = mock_client.request.call_args.kwargs
                assert call_kwargs["method"] == "DELETE"
                assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_given_request_without_query_when_proxying_then_no_query_string_appended(
        self, mock_settings: Mock
    ) -> None:
        """Given request without query params, when proxying, then no query string appended."""
        path = "srv/api/records/test-uuid"
        request = self._create_mock_request(method="GET", query="")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"<xml>test</xml>"
        mock_response.headers = {"content-type": "application/xml"}

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.request.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                await proxy_geonetwork(path, request)

                # Verify URL has no query string
                call_kwargs = mock_client.request.call_args.kwargs
                expected_url = f"{mock_settings.GEONETWORK_INTERNAL_URL}/{path}"
                assert call_kwargs["url"] == expected_url
                assert "?" not in call_kwargs["url"]


class TestGeoNetworkProxyAuthorization:
    """The proxy uses the GN service account: only allowed calls may go through."""

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("GET", "srv/api/registries/vocabularies/search"),
            ("POST", "srv/api/search/records/_search"),
        ],
    )
    def test_given_allowed_route_when_authorizing_then_passes(self, method: str, path: str):
        authorize_geonetwork_call(method, path, Mock(), Mock(), [])

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("DELETE", "srv/api/records/some-uuid"),
            ("PUT", "srv/api/users/1"),
            ("GET", "srv/api/me"),
            ("GET", "srv/api/site"),
            ("GET", "srv/api/records/../users/attachments"),
        ],
    )
    def test_given_other_route_when_authorizing_then_403(self, method: str, path: str):
        with pytest.raises(HTTPException) as exc_info:
            authorize_geonetwork_call(method, path, Mock(), Mock(), [])
        assert exc_info.value.status_code == 403

    def test_given_record_of_unknown_dataset_when_authorizing_then_403(self):
        session = Mock()
        session.exec.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            authorize_geonetwork_call(
                "POST", "srv/api/records/other-uuid/attachments", Mock(), session, []
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.parametrize(
        ("method", "level"),
        [("GET", AccessLevel.METADATA_READ), ("POST", AccessLevel.METADATA_WRITE)],
    )
    def test_given_record_of_dataset_when_authorizing_then_checks_dataset_access(
        self, method: str, level: AccessLevel
    ):
        session = Mock()
        session.exec.return_value.first.return_value = Mock(id="link-id")
        geo_ctx = Mock()
        with patch("src.api.routes.geonetwork.load_authorized_integrity_link") as check:
            authorize_geonetwork_call(
                method, "srv/api/records/md-uuid/attachments", geo_ctx, session, ["g"]
            )
        check.assert_called_once_with("link-id", level, geo_ctx, session, ["g"])


class TestGeoNetworkMe:
    """/me is answered from the geOrchestra user, never from the GN service account."""

    def test_given_user_when_calling_me_then_returns_georchestra_user(self):
        geo_ctx = GeorchestraContext(
            username="importer",
            roles={"IMPORT"},
            email="Importer@example.org",
            firstname="Imp",
            lastname="Orter",
            organization="Org",
        )

        body = json.loads(bytes(geonetwork_me(geo_ctx).body))

        assert body["username"] == "importer"
        assert body["email"] == "Importer@example.org"
        assert body["admin"] is False
        assert body["hash"] == hashlib.md5(b"importer@example.org").hexdigest()

    def test_given_anonymous_when_calling_me_then_204(self):
        geo_ctx = GeorchestraContext("", set(), "", "", "", "")
        assert geonetwork_me(geo_ctx).status_code == 204
