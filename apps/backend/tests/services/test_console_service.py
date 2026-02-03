from unittest.mock import MagicMock, patch

import httpx

from src.services.console_service import ConsoleService


class TestConsoleService:
    @patch("src.services.console_service.httpx.get")
    def test_get_organization_success(self, mock_get: MagicMock) -> None:
        """Test successful organization retrieval."""
        org_data = {"shortName": "org1", "name": "Organization One", "mail": "org1@example.com"}
        mock_response = MagicMock()
        mock_response.json.return_value = org_data
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        result = service.get_organization("org1")

        assert result == org_data
        mock_get.assert_called_once_with(
            "http://console.example.com/internal/organizations/shortname/org1", timeout=5.0
        )

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_not_found(self, mock_get: MagicMock) -> None:
        """Test organization not found (API returns 404)."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        result = service.get_organization("org_not_found")

        assert result is None

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_no_email_defined(self, mock_get: MagicMock) -> None:
        """Test organization found but email not defined — still returns the org dict."""
        org_data = {"shortName": "org1", "name": "Organization One"}
        mock_response = MagicMock()
        mock_response.json.return_value = org_data
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        result = service.get_organization("org1")

        assert result == org_data
        assert result is not None
        assert result.get("mail") is None

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_api_error(self, mock_get: MagicMock) -> None:
        """Test API error handling."""
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        service = ConsoleService("http://console.example.com")
        result = service.get_organization("org1")

        assert result is None

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_timeout(self, mock_get: MagicMock) -> None:
        """Test timeout handling."""
        mock_get.side_effect = httpx.TimeoutException("Timeout")

        service = ConsoleService("http://console.example.com")
        result = service.get_organization("org1")

        assert result is None

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_invalid_json(self, mock_get: MagicMock) -> None:
        """Test invalid JSON response handling."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        result = service.get_organization("org1")

        assert result is None
