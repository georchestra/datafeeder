from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi import HTTPException

from src.api.routes.geonetwork import proxy_geonetwork
from src.services.georchestra import GeorchestraContext


def _geo_ctx() -> GeorchestraContext:
    return GeorchestraContext(
        username="testuser",
        roles=set(),
        email="",
        firstname="",
        lastname="",
        organization="",
    )


class TestGeoNetworkProxy:
    """Test cases for GeoNetwork pass-through proxy."""

    @pytest.fixture
    def mock_session(self) -> Mock:
        """Create a mock database session."""
        return Mock()

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings for GeoNetwork connection."""
        settings = Mock()
        settings.GEONETWORK_URL = "http://geonetwork.example.com/geonetwork"
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
        self, mock_settings: Mock, mock_session: Mock
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

                response = await proxy_geonetwork(path, request, mock_session, _geo_ctx())

                # Verify correct URL with query string
                call_kwargs = mock_client.request.call_args.kwargs
                assert call_kwargs["method"] == "GET"
                expected_url = f"{mock_settings.GEONETWORK_URL}/{path}?{query}"
                assert call_kwargs["url"] == expected_url

                # Verify response
                assert response.status_code == 200
                assert response.body == b"<xml>test</xml>"

    @pytest.mark.asyncio
    async def test_given_post_request_when_proxying_then_forwards_body(
        self, mock_settings: Mock, mock_session: Mock
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

                response = await proxy_geonetwork(path, request, mock_session, _geo_ctx())

                # Verify body was forwarded
                call_kwargs = mock_client.request.call_args.kwargs
                assert call_kwargs["method"] == "POST"
                assert call_kwargs["content"] == body

                # Verify response preserves status
                assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_given_upstream_404_when_proxying_then_preserves_status(
        self, mock_settings: Mock, mock_session: Mock
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

                response = await proxy_geonetwork(path, request, mock_session, _geo_ctx())

                # Proxy should preserve the 404 status
                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_given_timeout_when_proxying_then_raises_504(self, mock_settings: Mock, mock_session: Mock) -> None:
        """Given upstream timeout, when proxying, then raises 504 error."""
        path = "srv/api/records"
        request = self._create_mock_request(method="GET")

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.request.side_effect = httpx.TimeoutException("Timeout")
                mock_client_class.return_value.__aenter__.return_value = mock_client

                with pytest.raises(HTTPException) as exc_info:
                    await proxy_geonetwork(path, request, mock_session, _geo_ctx())

                assert exc_info.value.status_code == 504

    @pytest.mark.asyncio
    async def test_given_connection_error_when_proxying_then_raises_502(
        self, mock_settings: Mock, mock_session: Mock
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
                    await proxy_geonetwork(path, request, mock_session, _geo_ctx())

                assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_given_put_request_when_proxying_then_forwards_body(
        self, mock_settings: Mock, mock_session: Mock
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

                response = await proxy_geonetwork(path, request, mock_session, _geo_ctx())

                # Verify body was forwarded
                call_kwargs = mock_client.request.call_args.kwargs
                assert call_kwargs["method"] == "PUT"
                assert call_kwargs["content"] == body
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_given_delete_request_when_proxying_then_forwards_correctly(
        self, mock_settings: Mock, mock_session: Mock
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

                response = await proxy_geonetwork(path, request, mock_session, _geo_ctx())

                # Verify method was forwarded
                call_kwargs = mock_client.request.call_args.kwargs
                assert call_kwargs["method"] == "DELETE"
                assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_given_request_without_query_when_proxying_then_no_query_string_appended(
        self, mock_settings: Mock, mock_session: Mock
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

                await proxy_geonetwork(path, request, mock_session, _geo_ctx())

                # Verify URL has no query string
                call_kwargs = mock_client.request.call_args.kwargs
                expected_url = f"{mock_settings.GEONETWORK_URL}/{path}"
                assert call_kwargs["url"] == expected_url
                assert "?" not in call_kwargs["url"]
