from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import jwt
import pytest
from airflow_client.client.exceptions import ConflictException, NotFoundException

from src.services.airflow_client import (
    _force_fail_dag_runs,  # pyright: ignore[reportPrivateUsage]
    _get_cached_airflow_api_client,  # pyright: ignore[reportPrivateUsage]
    _get_cached_dag_api,  # pyright: ignore[reportPrivateUsage]
    _get_cached_dag_run_api,  # pyright: ignore[reportPrivateUsage]
    _is_jwt_expired,  # pyright: ignore[reportPrivateUsage]
    _refresh_caches_if_token_expired,  # pyright: ignore[reportPrivateUsage]
    _request_new_access_token,  # pyright: ignore[reportPrivateUsage]
    cancel_ingestion_dag,
    delete_dag,
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
        settings.AIRFLOW_URL = "http://test-airflow.example.com"
        settings.AIRFLOW_USERNAME = "test_user"
        settings.AIRFLOW_PASSWORD = "test_pass"
        return settings

    @pytest.fixture
    def valid_jwt_token(self) -> str:
        """Generate a valid JWT token that expires in 1 hour."""
        payload = {
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "sub": "test_user",
        }
        return jwt.encode(payload, "secret_key_for_testing_only_padding_here", algorithm="HS256")

    @pytest.fixture
    def expired_jwt_token(self) -> str:
        """Generate an expired JWT token."""
        payload = {
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "sub": "test_user",
        }
        return jwt.encode(payload, "secret_key_for_testing_only_padding_here", algorithm="HS256")

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


class TestDeleteDag:
    def test_given_existing_dag_when_deleting_then_calls_delete(self) -> None:
        """Given an existing DAG, when deleting, then delete_dag API is called once."""
        with patch("src.services.airflow_client.get_dag_api") as mock_get_dag_api:
            mock_dag_api = Mock()
            mock_get_dag_api.return_value = mock_dag_api

            delete_dag("ingestion_123")

            mock_dag_api.delete_dag.assert_called_once_with("ingestion_123")

    def test_given_missing_dag_when_deleting_then_treats_as_success(self) -> None:
        """Given a DAG that does not exist, when deleting, then NotFoundException is swallowed."""
        with patch("src.services.airflow_client.get_dag_api") as mock_get_dag_api:
            mock_dag_api = Mock()
            mock_dag_api.delete_dag.side_effect = NotFoundException()
            mock_get_dag_api.return_value = mock_dag_api

            delete_dag("ingestion_123")  # must not raise

    def test_given_running_dag_when_deleting_then_force_fails_runs_and_retries(self) -> None:
        """Given a DAG with active runs, when deleting, then runs are force-failed and deletion is retried."""
        with (
            patch("src.services.airflow_client.get_dag_api") as mock_get_dag_api,
            patch("src.services.airflow_client._force_fail_dag_runs") as mock_force_fail,
        ):
            mock_dag_api = Mock()
            mock_dag_api.delete_dag.side_effect = [ConflictException(), None]
            mock_get_dag_api.return_value = mock_dag_api

            delete_dag("ingestion_123")

            mock_force_fail.assert_called_once_with("ingestion_123")
            assert mock_dag_api.delete_dag.call_count == 2

    def test_given_dag_disappears_between_conflict_and_retry_when_deleting_then_treats_as_success(
        self,
    ) -> None:
        """Given DAG disappears after force-fail, when retrying deletion, then NotFoundException is swallowed."""
        with (
            patch("src.services.airflow_client.get_dag_api") as mock_get_dag_api,
            patch("src.services.airflow_client._force_fail_dag_runs"),
        ):
            mock_dag_api = Mock()
            mock_dag_api.delete_dag.side_effect = [ConflictException(), NotFoundException()]
            mock_get_dag_api.return_value = mock_dag_api

            delete_dag("ingestion_123")  # must not raise


class TestForceFail:
    def test_given_missing_dag_when_force_failing_then_returns_silently(self) -> None:
        """Given a DAG that does not exist, when force-failing runs, then NotFoundException from get_dag_runs is swallowed."""
        with patch("src.services.airflow_client.get_dag_run_api") as mock_get_run_api:
            mock_run_api = Mock()
            mock_run_api.get_dag_runs.side_effect = NotFoundException()
            mock_get_run_api.return_value = mock_run_api

            _force_fail_dag_runs("ingestion_123")  # must not raise
            mock_run_api.patch_dag_run.assert_not_called()


class TestCancelIngestionDag:
    def test_force_fails_ingestion_process_and_staging_runs(self) -> None:
        """All in-flight runs of the dataset are force-failed: the scheduled
        ingestion DAG, plus process_dag and staging_dag runs by run-id prefix."""
        with patch("src.services.airflow_client._force_fail_dag_runs") as mock_force_fail:
            cancel_ingestion_dag("abc-123")

        mock_force_fail.assert_any_call("ingestion_abc-123")
        mock_force_fail.assert_any_call("process_dag", dag_run_id_prefix="abc-123_")
        mock_force_fail.assert_any_call("staging_dag", dag_run_id_prefix="abc-123")
        assert mock_force_fail.call_count == 3
