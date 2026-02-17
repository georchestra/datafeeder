from unittest.mock import Mock, patch

import httpx
import pytest
from fastapi import HTTPException

from src.api.routes.groups_common import GroupItem, fetch_groups


class TestFetchGroups:
    """Tests for the shared fetch_groups helper."""

    def test_given_valid_upstream_when_fetching_then_returns_group_items(self) -> None:
        """Given a valid upstream response, when fetching, then returns mapped GroupItem list."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "name": "Group A"},
            {"id": "2", "name": "Group B"},
        ]

        with patch("src.api.routes.groups_common.httpx.get", return_value=mock_response):
            result = fetch_groups(
                url="http://example.com/groups",
                id_field="id",
                label_field="name",
            )

        assert result == [
            GroupItem(id="1", label="Group A"),
            GroupItem(id="2", label="Group B"),
        ]

    def test_given_upstream_timeout_when_fetching_then_raises_502(self) -> None:
        """Given an upstream timeout, when fetching, then raises HTTPException 502."""
        with patch(
            "src.api.routes.groups_common.httpx.get",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                fetch_groups(
                    url="http://example.com/groups",
                    id_field="id",
                    label_field="name",
                )
            assert exc_info.value.status_code == 502

    def test_given_upstream_error_status_when_fetching_then_raises_502(self) -> None:
        """Given an upstream error status, when fetching, then raises HTTPException 502."""
        mock_response = Mock()
        mock_response.status_code = 500

        with patch("src.api.routes.groups_common.httpx.get", return_value=mock_response):
            with pytest.raises(HTTPException) as exc_info:
                fetch_groups(
                    url="http://example.com/groups",
                    id_field="id",
                    label_field="name",
                )
            assert exc_info.value.status_code == 502

    def test_given_empty_upstream_when_fetching_then_returns_empty_list(self) -> None:
        """Given an empty upstream response, when fetching, then returns empty list."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch("src.api.routes.groups_common.httpx.get", return_value=mock_response):
            result = fetch_groups(
                url="http://example.com/groups",
                id_field="id",
                label_field="name",
            )

        assert result == []

    def test_given_auth_provided_when_fetching_then_passes_credentials(self) -> None:
        """Given auth credentials, when fetching, then passes them to httpx."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch(
            "src.api.routes.groups_common.httpx.get", return_value=mock_response
        ) as mock_get:
            fetch_groups(
                url="http://example.com/groups",
                id_field="id",
                label_field="name",
                username="user",
                password="pass",
            )

        mock_get.assert_called_once_with(
            "http://example.com/groups",
            auth=("user", "pass"),
            timeout=10.0,
        )

    def test_given_no_auth_when_fetching_then_no_credentials(self) -> None:
        """Given no auth credentials, when fetching, then passes auth=None."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []

        with patch(
            "src.api.routes.groups_common.httpx.get", return_value=mock_response
        ) as mock_get:
            fetch_groups(
                url="http://example.com/groups",
                id_field="id",
                label_field="name",
            )

        mock_get.assert_called_once_with(
            "http://example.com/groups",
            auth=None,
            timeout=10.0,
        )

    def test_given_missing_fields_when_fetching_then_skips_items(self) -> None:
        """Given items with missing fields, when fetching, then skips those items."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"id": "1", "name": "Group A"},
            {"id": "2"},  # missing "name"
            {"name": "Group C"},  # missing "id"
            {"id": "4", "name": "Group D"},
        ]

        with patch("src.api.routes.groups_common.httpx.get", return_value=mock_response):
            result = fetch_groups(
                url="http://example.com/groups",
                id_field="id",
                label_field="name",
            )

        assert result == [
            GroupItem(id="1", label="Group A"),
            GroupItem(id="4", label="Group D"),
        ]

    def test_given_connect_error_when_fetching_then_raises_502(self) -> None:
        """Given a connection error, when fetching, then raises HTTPException 502."""
        with patch(
            "src.api.routes.groups_common.httpx.get",
            side_effect=httpx.ConnectError("connection refused"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                fetch_groups(
                    url="http://example.com/groups",
                    id_field="id",
                    label_field="name",
                )
            assert exc_info.value.status_code == 502
