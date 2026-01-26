from unittest.mock import MagicMock, patch

import httpx

from src.services.console_service import ConsoleService


class TestConsoleService:
    @patch("src.services.console_service.httpx.get")
    def test_get_organization_email_success(self, mock_get: MagicMock) -> None:
        """Test successful organization email retrieval."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {"shortName": "org1", "mail": "org1@example.com"}

        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        email = service.get_organization_email("org1")

        assert email == "org1@example.com"
        mock_get.assert_called_once_with(
            "http://console.example.com/internal/organizations/shortname/org1", timeout=5.0
        )

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_email_not_found(self, mock_get: MagicMock) -> None:
        """Test organization not found in API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"shortName": "org1", "mail": "org1@example.com"},
        ]
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        email = service.get_organization_email("org_not_found")

        assert email is None

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_email_no_email_defined(self, mock_get: MagicMock) -> None:
        """Test organization found but email not defined."""
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"shortName": "org1"},  # No mail field
            {"shortName": "org2", "mail": None},  # Mail is None
        ]
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        email1 = service.get_organization_email("org1")
        email2 = service.get_organization_email("org2")

        assert email1 is None
        assert email2 is None

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_email_api_error(self, mock_get: MagicMock) -> None:
        """Test API error handling."""
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        service = ConsoleService("http://console.example.com")
        email = service.get_organization_email("org1")

        assert email is None

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_email_timeout(self, mock_get: MagicMock) -> None:
        """Test timeout handling."""
        mock_get.side_effect = httpx.TimeoutException("Timeout")

        service = ConsoleService("http://console.example.com")
        email = service.get_organization_email("org1")

        assert email is None

    @patch("src.services.console_service.httpx.get")
    def test_get_organization_email_invalid_json(self, mock_get: MagicMock) -> None:
        """Test invalid JSON response handling."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        email = service.get_organization_email("org1")

        assert email is None
