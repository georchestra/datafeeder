from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import jwt
import pytest

from src.services.airflow_client import (
    _get_cached_airflow_api_client,  # pyright: ignore[reportPrivateUsage]
    _get_cached_dag_api,  # pyright: ignore[reportPrivateUsage]
    _get_cached_dag_run_api,  # pyright: ignore[reportPrivateUsage]
    _is_jwt_expired,  # pyright: ignore[reportPrivateUsage]
    _refresh_caches_if_token_expired,  # pyright: ignore[reportPrivateUsage]
    _request_new_access_token,  # pyright: ignore[reportPrivateUsage]
    get_airflow_api_client,
    get_dag_api,
    get_dag_run_api,
)


class TestAirflowClient:
    """Test cases for Airflow client service."""

    @pytest.fixture(autouse=True)
    def clear_caches(self) -> None:
        """Clear all LRU caches before each test to ensure test isolation."""
        _get_cached_airflow_api_client.cache_clear()
        _get_cached_dag_run_api.cache_clear()
        _get_cached_dag_api.cache_clear()

    @pytest.fixture
    def mock_settings(self) -> Mock:
        """Create mock settings for Airflow connection."""
        settings = Mock()
        settings.datakern_config.get.return_value = "http://test-airflow.example.com"
        settings.AIRFLOW_USERNAME = "test_user"
        settings.AIRFLOW_PASSWORD = "test_pass"

        def datakern_config_get(key: str, default: str = "") -> str:
            if key == "AIRFLOW_USERNAME" or key == "airflow_username":
                return "test_user"
            elif key == "AIRFLOW_PASSWORD" or key == "airflow_password":
                return "test_pass"
            elif key == "airflow_url":
                return "http://test-airflow.example.com"
            return default

        settings.datakern_config.get.side_effect = datakern_config_get
        return settings

    @pytest.fixture
    def valid_jwt_token(self) -> str:
        """Generate a valid JWT token that expires in 1 hour."""
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "sub": "test_user",
        }
        return jwt.encode(payload, "secret", algorithm="HS256")

    @pytest.fixture
    def expired_jwt_token(self) -> str:
        """Generate an expired JWT token."""
        payload = {
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "sub": "test_user",
        }
        return jwt.encode(payload, "secret", algorithm="HS256")

    def test_given_valid_credentials_when_requesting_new_token_then_returns_token_successfully(
        self, mock_settings: Mock
    ) -> None:
        """Given valid Airflow credentials, when requesting a new access token, then returns token successfully."""
        # Given: valid Airflow credentials are configured
        # And: The Airflow API returns a successful response with a token
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch("src.services.airflow_client.requests.post") as mock_post,
        ):
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"access_token": "test_token_123"}
            mock_post.return_value = mock_response

            # When: A new access token is requested
            token = _request_new_access_token()

            # Then: The token is returned successfully
            assert token == "test_token_123"
            # And: The correct API endpoint was called with credentials
            mock_post.assert_called_once_with(
                "http://test-airflow.example.com/auth/token",
                json={"username": "test_user", "password": "test_pass"},
                headers={"Content-Type": "application/json"},
            )

    def test_given_invalid_credentials_when_requesting_new_token_then_raises_runtime_error(
        self, mock_settings: Mock
    ) -> None:
        """Given invalid credentials, when requesting a new access token, then raises RuntimeError."""
        # Given: Invalid Airflow credentials
        # And: The Airflow API returns an unauthorized response
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch("src.services.airflow_client.requests.post") as mock_post,
        ):
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_post.return_value = mock_response

            # When: A new access token is requested
            # Then: A RuntimeError is raised
            with pytest.raises(RuntimeError, match="Failed to get access token: 401"):
                _request_new_access_token()

    def test_given_malformed_response_when_requesting_new_token_then_raises_validation_error(
        self, mock_settings: Mock
    ) -> None:
        """Given a malformed response, when requesting a new access token, then raises validation error."""
        # Given: The Airflow API returns a response with missing access_token field
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch("src.services.airflow_client.requests.post") as mock_post,
        ):
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"wrong_field": "value"}
            mock_post.return_value = mock_response

            # When: A new access token is requested
            # Then: A validation error is raised
            with pytest.raises(Exception):  # Pydantic validation error
                _request_new_access_token()

    def test_given_valid_jwt_token_when_checking_expiration_then_returns_false(
        self, valid_jwt_token: str
    ) -> None:
        """Given a valid JWT token, when checking expiration, then returns False."""
        # Given: A valid JWT token that expires in 1 hour
        # When: Checking if the token is expired
        result = _is_jwt_expired(valid_jwt_token)

        # Then: The token is not expired
        assert result is False

    def test_given_expired_jwt_token_when_checking_expiration_then_returns_true(
        self, expired_jwt_token: str
    ) -> None:
        """Given an expired JWT token, when checking expiration, then returns True."""
        # Given: An expired JWT token
        # When: Checking if the token is expired
        result = _is_jwt_expired(expired_jwt_token)

        # Then: The token is expired
        assert result is True

    def test_given_invalid_jwt_token_when_checking_expiration_then_raises_runtime_error(
        self,
    ) -> None:
        """Given an invalid JWT token, when checking expiration, then raises RuntimeError."""
        # Given: An invalid JWT token
        # When: Checking if the token is expired
        # Then: A RuntimeError is raised
        with pytest.raises(RuntimeError, match="Invalid JWT token"):
            _is_jwt_expired("not_a_valid_jwt_token")

    def test_given_malformed_jwt_token_when_checking_expiration_then_raises_runtime_error(
        self,
    ) -> None:
        """Given a malformed JWT token, when checking expiration, then raises RuntimeError."""
        # Given: A malformed JWT token (incomplete)
        # When: Checking if the token is expired
        # Then: A RuntimeError is raised
        with pytest.raises(RuntimeError, match="Invalid JWT token"):
            _is_jwt_expired("header.payload")

    def test_given_valid_settings_when_getting_cached_client_then_creates_configured_api_client(
        self, mock_settings: Mock, valid_jwt_token: str
    ) -> None:
        """Given valid settings, when getting cached API client, then creates properly configured API client."""
        # Given: Valid Airflow settings and a valid JWT token
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ),
            patch("src.services.airflow_client.Configuration") as mock_config_class,
            patch("src.services.airflow_client.ApiClient") as mock_api_client_class,
        ):
            mock_config = Mock()
            mock_config_class.return_value = mock_config
            mock_api_client = Mock()
            mock_api_client_class.return_value = mock_api_client

            # When: Getting the cached Airflow API client
            client = _get_cached_airflow_api_client()

            # Then: The API client is created with proper configuration
            assert client == mock_api_client
            mock_config_class.assert_called_once_with(host="http://test-airflow.example.com")
            assert mock_config.access_token == valid_jwt_token
            mock_api_client_class.assert_called_once_with(configuration=mock_config)

    def test_given_existing_cached_client_when_getting_client_again_then_reuses_cached_instance(
        self, mock_settings: Mock, valid_jwt_token: str
    ) -> None:
        """Given an existing cached client, when getting client again, then reuses the cached instance."""
        # Given: Valid settings and mocked dependencies
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ) as mock_token_request,
            patch("src.services.airflow_client.Configuration"),
            patch("src.services.airflow_client.ApiClient"),
        ):
            # When: Getting the API client twice
            client1 = _get_cached_airflow_api_client()
            client2 = _get_cached_airflow_api_client()

            # Then: The same client instance is returned
            assert client1 is client2
            # And: The token is only requested once due to caching
            assert mock_token_request.call_count == 1

    def test_given_valid_token_when_refreshing_caches_then_caches_are_preserved(
        self, mock_settings: Mock, valid_jwt_token: str
    ) -> None:
        """Given a valid token, when refreshing caches, then caches are preserved."""
        # Given: Valid settings and a client with a valid token
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ),
            patch("src.services.airflow_client.Configuration"),
            patch("src.services.airflow_client.ApiClient") as mock_api_client_class,
        ):
            mock_client = Mock()
            mock_config = Mock()
            mock_config.access_token = valid_jwt_token
            mock_client.configuration = mock_config
            mock_api_client_class.return_value = mock_client

            # And: Populated caches
            _get_cached_airflow_api_client()
            _get_cached_dag_run_api()
            _get_cached_dag_api()

            cache_info_before = _get_cached_airflow_api_client.cache_info()

            # When: Refreshing caches
            _refresh_caches_if_token_expired()

            # Then: Caches are preserved (not cleared)
            cache_info_after = _get_cached_airflow_api_client.cache_info()
            assert cache_info_after.hits == cache_info_before.hits + 1

    def test_given_expired_token_when_refreshing_caches_then_caches_are_cleared(
        self, mock_settings: Mock, expired_jwt_token: str, valid_jwt_token: str
    ) -> None:
        """Given an expired token, when refreshing caches, then caches are cleared."""
        # Given: Valid settings and API client dependencies
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch("src.services.airflow_client.Configuration"),
            patch("src.services.airflow_client.ApiClient") as mock_api_client_class,
        ):
            # And: A client with an expired token
            with patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=expired_jwt_token,
            ):
                mock_client = Mock()
                mock_config = Mock()
                mock_config.access_token = expired_jwt_token
                mock_client.configuration = mock_config
                mock_api_client_class.return_value = mock_client
                _get_cached_airflow_api_client()

            # When: Refreshing caches with a new valid token available
            with patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ):
                _refresh_caches_if_token_expired()

                # Then: Caches are cleared due to expired token
                cache_info = _get_cached_airflow_api_client.cache_info()
                assert cache_info.currsize == 0

    def test_given_none_token_when_refreshing_caches_then_caches_are_cleared(
        self, mock_settings: Mock, valid_jwt_token: str
    ) -> None:
        """Given a None token, when refreshing caches, then caches are cleared."""
        # Given: Valid settings and a client with no access token
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ),
            patch("src.services.airflow_client.Configuration"),
            patch("src.services.airflow_client.ApiClient") as mock_api_client_class,
        ):
            mock_client = Mock()
            mock_config = Mock()
            mock_config.access_token = None
            mock_client.configuration = mock_config
            mock_api_client_class.return_value = mock_client

            _get_cached_airflow_api_client()

            cache_size_before = _get_cached_airflow_api_client.cache_info().currsize

            # When: Refreshing caches
            _refresh_caches_if_token_expired()

            # Then: Caches are cleared because token is None
            cache_size_after = _get_cached_airflow_api_client.cache_info().currsize
            assert cache_size_before == 1
            assert cache_size_after == 0

    def test_given_valid_settings_when_getting_airflow_client_then_refreshes_and_returns_client(
        self, mock_settings: Mock, valid_jwt_token: str
    ) -> None:
        """Given valid settings, when getting Airflow API client, then refreshes caches and returns client."""
        # Given: Valid Airflow settings and JWT token
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ),
            patch("src.services.airflow_client.Configuration"),
            patch("src.services.airflow_client.ApiClient") as mock_api_client_class,
        ):
            mock_client = Mock()
            mock_config = Mock()
            mock_config.access_token = valid_jwt_token
            mock_client.configuration = mock_config
            mock_api_client_class.return_value = mock_client

            # When: Getting the Airflow API client
            client = get_airflow_api_client()

            # Then: The client is returned after refreshing caches
            assert client == mock_client

    def test_given_valid_settings_when_getting_dag_run_api_then_creates_and_returns_api_instance(
        self, mock_settings: Mock, valid_jwt_token: str
    ) -> None:
        """Given valid settings, when getting DAG run API, then creates and returns DagRunApi instance."""
        # Given: Valid Airflow settings and mocked dependencies
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ),
            patch("src.services.airflow_client.Configuration"),
            patch("src.services.airflow_client.ApiClient") as mock_api_client_class,
            patch("src.services.airflow_client.DagRunApi") as mock_dag_run_api_class,
        ):
            mock_client = Mock()
            mock_config = Mock()
            mock_config.access_token = valid_jwt_token
            mock_client.configuration = mock_config
            mock_api_client_class.return_value = mock_client

            mock_dag_run_api = Mock()
            mock_dag_run_api_class.return_value = mock_dag_run_api

            # When: Getting the DAG run API
            api = get_dag_run_api()

            # Then: The DagRunApi instance is created and returned
            assert api == mock_dag_run_api
            assert mock_dag_run_api_class.called

    def test_given_valid_settings_when_getting_dag_api_then_creates_and_returns_api_instance(
        self, mock_settings: Mock, valid_jwt_token: str
    ) -> None:
        """Given valid settings, when getting DAG API, then creates and returns DAGApi instance."""
        # Given: Valid Airflow settings and mocked dependencies
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ),
            patch("src.services.airflow_client.Configuration"),
            patch("src.services.airflow_client.ApiClient") as mock_api_client_class,
            patch("src.services.airflow_client.DAGApi") as mock_dag_api_class,
        ):
            mock_client = Mock()
            mock_config = Mock()
            mock_config.access_token = valid_jwt_token
            mock_client.configuration = mock_config
            mock_api_client_class.return_value = mock_client

            mock_dag_api = Mock()
            mock_dag_api_class.return_value = mock_dag_api

            # When: Getting the DAG API
            api = get_dag_api()

            # Then: The DAGApi instance is created and returned
            assert api == mock_dag_api
            assert mock_dag_api_class.called

    def test_given_multiple_dag_api_calls_when_getting_apis_then_reuses_cached_client(
        self, mock_settings: Mock, valid_jwt_token: str
    ) -> None:
        """Given multiple DAG API calls, when getting APIs, then reuses the cached API client."""
        # Given: Valid settings and mocked dependencies
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ),
            patch("src.services.airflow_client.Configuration"),
            patch("src.services.airflow_client.ApiClient") as mock_api_client_class,
            patch("src.services.airflow_client.DagRunApi"),
            patch("src.services.airflow_client.DAGApi"),
        ):
            mock_client = Mock()
            mock_config = Mock()
            mock_config.access_token = valid_jwt_token
            mock_client.configuration = mock_config
            mock_api_client_class.return_value = mock_client

            # When: Getting both DAG APIs
            get_dag_run_api()
            get_dag_api()

            # Then: The API client is only created once due to caching
            assert mock_api_client_class.call_count == 1

    def test_given_expired_token_in_caches_when_refreshing_then_all_dependent_caches_are_cleared(
        self, mock_settings: Mock, expired_jwt_token: str, valid_jwt_token: str
    ) -> None:
        """Given expired token in caches, when refreshing, then all dependent caches are cleared."""
        # Given: Valid settings and mocked dependencies
        with (
            patch("src.services.airflow_client.get_settings", return_value=mock_settings),
            patch("src.services.airflow_client.Configuration"),
            patch("src.services.airflow_client.ApiClient") as mock_api_client_class,
            patch("src.services.airflow_client.DagRunApi"),
            patch("src.services.airflow_client.DAGApi"),
        ):
            # And: All caches populated with expired token
            with patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=expired_jwt_token,
            ):
                mock_client = Mock()
                mock_config = Mock()
                mock_config.access_token = expired_jwt_token
                mock_client.configuration = mock_config
                mock_api_client_class.return_value = mock_client

                get_airflow_api_client()
                get_dag_run_api()
                get_dag_api()

            # And: All caches have entries
            assert _get_cached_airflow_api_client.cache_info().currsize == 1

            # When: Refreshing caches with new valid token
            with patch(
                "src.services.airflow_client._request_new_access_token",
                return_value=valid_jwt_token,
            ):
                _refresh_caches_if_token_expired()

            # Then: All caches are cleared due to token expiration
            assert _get_cached_airflow_api_client.cache_info().currsize == 0
            assert _get_cached_dag_run_api.cache_info().currsize == 0
            assert _get_cached_dag_api.cache_info().currsize == 0
