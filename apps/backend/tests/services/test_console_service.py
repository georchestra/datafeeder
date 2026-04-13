from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.services.console_service import ConsoleService, ConsoleServiceError


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

    @patch("src.services.console_service.httpx.get")
    def test_get_all_organizations_success(self, mock_get: MagicMock) -> None:
        """Test successful retrieval of all organizations."""
        orgs = [
            {"id": "uuid-1", "shortName": "C2C", "name": "Camptocamp"},
            {"id": "uuid-2", "shortName": "GEO", "name": "GeoOrg"},
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = orgs
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        result = service.get_all_organizations()

        assert result == orgs
        mock_get.assert_called_once_with(
            "http://console.example.com/internal/organizations", timeout=5.0
        )

    @patch("src.services.console_service.httpx.get")
    def test_get_all_organizations_http_error_raises(self, mock_get: MagicMock) -> None:
        """Test that HTTP errors are propagated."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=MagicMock(status_code=500)
        )
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")

        with pytest.raises(httpx.HTTPStatusError):
            service.get_all_organizations()

    @patch("src.services.console_service.httpx.get")
    def test_get_all_organizations_invalid_json_raises(self, mock_get: MagicMock) -> None:
        """Test that malformed JSON response raises ValueError with a clear message."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")

        with pytest.raises(ValueError, match="Console returned invalid JSON from"):
            service.get_all_organizations()

    @patch("src.services.console_service.httpx.get")
    def test_get_all_roles_success(self, mock_get: MagicMock) -> None:
        """Test successful retrieval of all roles."""
        roles = [
            {"id": "uuid-1", "name": "ROLE_ADMIN"},
            {"id": "uuid-2", "name": "ROLE_USER"},
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = roles
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")
        result = service.get_all_roles()

        assert result == roles
        mock_get.assert_called_once_with("http://console.example.com/internal/roles", timeout=5.0)

    @patch("src.services.console_service.httpx.get")
    def test_get_all_roles_http_error_raises(self, mock_get: MagicMock) -> None:
        """HTTP errors are wrapped in ConsoleServiceError."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=MagicMock(status_code=500)
        )
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")

        with pytest.raises(ConsoleServiceError):
            service.get_all_roles()

    @patch("src.services.console_service.httpx.get")
    def test_get_all_roles_invalid_json_raises(self, mock_get: MagicMock) -> None:
        """Malformed JSON response is wrapped in ConsoleServiceError."""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_get.return_value = mock_response

        service = ConsoleService("http://console.example.com")

        with pytest.raises(ConsoleServiceError):
            service.get_all_roles()

    @patch("src.services.console_service.httpx.get")
    def test_get_all_roles_network_error_raises(self, mock_get: MagicMock) -> None:
        """Network errors are wrapped in ConsoleServiceError."""
        mock_get.side_effect = httpx.ConnectError("Connection refused")

        service = ConsoleService("http://console.example.com")

        with pytest.raises(ConsoleServiceError, match="Failed to fetch roles from console API"):
            service.get_all_roles()
