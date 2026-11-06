from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
import requests

from src.api.deps import get_geonetwork_credentials
from src.api.routes import geonetwork as geonetwork_route
from src.services.console_service import ConsoleService
from src.services.directory import get_directory_service
from src.services.keycloak_auth import (
    KeycloakHttpxAuth,
    KeycloakRequestsAuth,
    KeycloakTokenError,
    KeycloakTokenProvider,
)
from src.services.keycloak_directory_service import KeycloakDirectoryService

MODULE = "src.services.keycloak_auth"


def _token_response(token: str, expires_in: int = 300) -> MagicMock:
    response = MagicMock()
    response.json.return_value = {"access_token": token, "expires_in": expires_in}
    return response


class TestKeycloakTokenProvider:
    @patch(f"{MODULE}.httpx.post")
    def test_fetches_client_credentials_token_once(self, mock_post: MagicMock) -> None:
        mock_post.return_value = _token_response("t1")
        provider = KeycloakTokenProvider("http://kc/", "georchestra", "datafeeder", "secret")

        assert provider.get_token() == "t1"
        assert provider.get_token() == "t1"

        mock_post.assert_called_once()
        assert mock_post.call_args.args[0] == (
            "http://kc/realms/georchestra/protocol/openid-connect/token"
        )
        assert mock_post.call_args.kwargs["data"] == {
            "grant_type": "client_credentials",
            "client_id": "datafeeder",
            "client_secret": "secret",
        }

    @patch(f"{MODULE}.httpx.post")
    def test_renews_expired_token(self, mock_post: MagicMock) -> None:
        """A token expiring within the safety margin is renewed on next use."""
        mock_post.side_effect = [_token_response("t1", expires_in=10), _token_response("t2")]
        provider = KeycloakTokenProvider("http://kc", "georchestra", "datafeeder", "secret")

        assert provider.get_token() == "t1"
        assert provider.get_token() == "t2"

    @patch(f"{MODULE}.httpx.post")
    def test_invalidate_forces_renewal(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = [_token_response("t1"), _token_response("t2")]
        provider = KeycloakTokenProvider("http://kc", "georchestra", "datafeeder", "secret")

        provider.get_token()
        provider.invalidate()

        assert provider.get_token() == "t2"

    @patch(f"{MODULE}.httpx.post")
    def test_raises_on_error(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = httpx.ConnectError("down")
        provider = KeycloakTokenProvider("http://kc", "georchestra", "datafeeder", "secret")

        with pytest.raises(KeycloakTokenError):
            provider.get_token()


class TestAuthAdapters:
    def test_httpx_auth_sets_bearer_and_retries_once_on_401(self) -> None:
        provider = MagicMock()
        provider.get_token.side_effect = ["t1", "t2"]
        flow = KeycloakHttpxAuth(provider).auth_flow(httpx.Request("GET", "http://gn"))

        request = next(flow)
        assert request.headers["Authorization"] == "Bearer t1"

        retried = flow.send(httpx.Response(401))
        assert retried.headers["Authorization"] == "Bearer t2"
        provider.invalidate.assert_called_once()

    def test_requests_auth_sets_bearer(self) -> None:
        provider = MagicMock()
        provider.get_token.return_value = "t1"
        request = requests.Request("GET", "http://gn").prepare()

        KeycloakRequestsAuth(provider)(request)

        assert request.headers["Authorization"] == "Bearer t1"


class TestDirectoryServiceFactory:
    @patch("src.services.directory.get_settings")
    def test_console_by_default(self, mock_settings: Mock) -> None:
        mock_settings.return_value = Mock(
            DIRECTORY_PROVIDER="console", CONSOLE_INTERNAL_URL="http://console"
        )

        service = get_directory_service()

        assert isinstance(service, ConsoleService)
        assert service.console_url == "http://console"

    @patch("src.services.directory.get_settings")
    def test_keycloak(self, mock_settings: Mock) -> None:
        mock_settings.return_value = Mock(
            DIRECTORY_PROVIDER="keycloak",
            KEYCLOAK_INTERNAL_URL="http://kc",
            KEYCLOAK_REALM="georchestra",
            KEYCLOAK_CLIENT_ID="datafeeder",
            KEYCLOAK_CLIENT_SECRET="secret",
            KEYCLOAK_ORG_GROUP_PATH="",
            KEYCLOAK_ORG_NAME_ATTRIBUTE="o",
            KEYCLOAK_ORG_MAIL_ATTRIBUTE="mail",
            KEYCLOAK_ORG_CODE_ATTRIBUTE="",
        )

        service = get_directory_service()

        assert isinstance(service, KeycloakDirectoryService)
        assert service.admin_url == "http://kc/admin/realms/georchestra"


class TestGeoNetworkAuthSelection:
    @patch("src.api.deps.get_settings")
    def test_basic_auth_by_default(self, mock_settings: Mock) -> None:
        mock_settings.return_value = Mock(
            GEONETWORK_AUTH="basic", GEONETWORK_USERNAME="u", GEONETWORK_PASSWORD="p"
        )

        assert get_geonetwork_credentials() == ("u", "p")

    @patch("src.api.deps.get_token_provider")
    @patch("src.api.deps.get_settings")
    def test_keycloak_bearer(self, mock_settings: Mock, mock_provider: Mock) -> None:
        mock_settings.return_value = Mock(GEONETWORK_AUTH="keycloak")

        credentials = get_geonetwork_credentials()

        assert isinstance(credentials, KeycloakRequestsAuth)
        assert credentials.provider is mock_provider.return_value

    @patch("src.api.routes.geonetwork.get_token_provider")
    @patch("src.api.routes.geonetwork.get_settings")
    def test_proxy_keycloak_bearer(self, mock_settings: Mock, mock_provider: Mock) -> None:
        mock_settings.return_value = Mock(GEONETWORK_AUTH="keycloak")

        auth = geonetwork_route._get_geonetwork_auth()  # pyright: ignore[reportPrivateUsage]

        assert isinstance(auth, KeycloakHttpxAuth)
