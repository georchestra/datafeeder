from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from fastapi import HTTPException

from src.api.routes.geonetwork import get_metadata_xml


class TestGeoNetworkRoute:
    """Test cases for GeoNetwork proxy routes."""

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings for GeoNetwork connection."""
        settings = Mock()
        settings.GEONETWORK_URL = "http://test-geonetwork.example.com/geonetwork"
        settings.GEONETWORK_USERNAME = "test_user"
        settings.GEONETWORK_PASSWORD = "test_pass"
        return settings

    @pytest.fixture
    def sample_metadata_xml(self) -> bytes:
        """Return sample metadata XML content."""
        return b"""<?xml version="1.0" encoding="UTF-8"?>
        <gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd">
            <gmd:fileIdentifier>
                <gco:CharacterString xmlns:gco="http://www.isotc211.org/2005/gco">
                    test-uuid-1234
                </gco:CharacterString>
            </gmd:fileIdentifier>
        </gmd:MD_Metadata>"""

    @pytest.mark.asyncio
    async def test_given_valid_uuid_when_fetching_metadata_then_returns_xml_response(
        self, mock_settings: Mock, sample_metadata_xml: bytes
    ) -> None:
        """Given a valid UUID, when fetching metadata, then returns XML response."""
        # Given: A valid metadata UUID exists in GeoNetwork
        uuid = "test-uuid-1234"
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = sample_metadata_xml
        mock_response.raise_for_status = Mock()

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # When: Fetching metadata XML
                response = await get_metadata_xml(uuid)

                # Then: Returns XML content with correct media type
                assert response.body == sample_metadata_xml
                assert response.media_type == "application/xml"

                # And: The correct GeoNetwork URL was called
                mock_client.get.assert_called_once_with(
                    f"{mock_settings.GEONETWORK_URL}/srv/api/records/{uuid}/formatters/xml",
                    auth=(
                        mock_settings.GEONETWORK_USERNAME,
                        mock_settings.GEONETWORK_PASSWORD,
                    ),
                    timeout=30.0,
                )

    @pytest.mark.asyncio
    async def test_given_nonexistent_uuid_when_fetching_metadata_then_raises_404(
        self, mock_settings: Mock
    ) -> None:
        """Given a nonexistent UUID, when fetching metadata, then raises 404 error."""
        # Given: A UUID that does not exist in GeoNetwork
        uuid = "nonexistent-uuid"
        mock_response = Mock()
        mock_response.status_code = 404

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # When: Fetching metadata XML
                # Then: Raises HTTPException with 404 status
                with pytest.raises(HTTPException) as exc_info:
                    await get_metadata_xml(uuid)

                assert exc_info.value.status_code == 404
                assert exc_info.value.detail == "Metadata not found"

    @pytest.mark.asyncio
    async def test_given_geonetwork_timeout_when_fetching_metadata_then_raises_504(
        self, mock_settings: Mock
    ) -> None:
        """Given GeoNetwork timeout, when fetching metadata, then raises 504 error."""
        # Given: GeoNetwork times out
        uuid = "test-uuid-1234"

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # When: Fetching metadata XML
                # Then: Raises HTTPException with 504 status
                with pytest.raises(HTTPException) as exc_info:
                    await get_metadata_xml(uuid)

                assert exc_info.value.status_code == 504
                assert exc_info.value.detail == "GeoNetwork request timeout"

    @pytest.mark.asyncio
    async def test_given_geonetwork_server_error_when_fetching_metadata_then_raises_502(
        self, mock_settings: Mock
    ) -> None:
        """Given GeoNetwork server error, when fetching metadata, then raises 502 error."""
        # Given: GeoNetwork returns a 500 server error
        uuid = "test-uuid-1234"
        mock_response = Mock()
        mock_response.status_code = 500

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get.return_value = mock_response
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Server Error",
                    request=Mock(),
                    response=mock_response,
                )
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # When: Fetching metadata XML
                # Then: Raises HTTPException with 502 status
                with pytest.raises(HTTPException) as exc_info:
                    await get_metadata_xml(uuid)

                assert exc_info.value.status_code == 502
                assert "GeoNetwork error: 500" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_given_connection_error_when_fetching_metadata_then_raises_502(
        self, mock_settings: Mock
    ) -> None:
        """Given connection error, when fetching metadata, then raises 502 error."""
        # Given: Cannot connect to GeoNetwork
        uuid = "test-uuid-1234"

        with patch("src.api.routes.geonetwork.get_settings", return_value=mock_settings):
            with patch("src.api.routes.geonetwork.httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.get.side_effect = Exception("Connection refused")
                mock_client_class.return_value.__aenter__.return_value = mock_client

                # When: Fetching metadata XML
                # Then: Raises HTTPException with 502 status
                with pytest.raises(HTTPException) as exc_info:
                    await get_metadata_xml(uuid)

                assert exc_info.value.status_code == 502
                assert exc_info.value.detail == "Failed to connect to GeoNetwork"
