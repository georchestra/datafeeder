from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.routes.data_groups import list_groups
from src.api.routes.groups_common import GroupItem


class TestDataGroups:
    """Tests for the data groups route."""

    def _mock_settings(self, filter_regex: str = "") -> MagicMock:
        mock_settings = MagicMock()
        mock_settings.CONSOLE_URL = "http://console.example.com"
        mock_settings.DATA_GROUPS_LABEL_FILTER_REGEX = filter_regex
        return mock_settings

    def test_given_roles_when_listing_then_returns_group_items(self) -> None:
        """Given console roles, when listing data groups, then returns mapped GroupItem list."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_roles.return_value = [
                {"id": "role-uuid-1", "name": "ROLE_ADMIN", "description": ""},
                {"id": "role-uuid-2", "name": "ROLE_USER", "description": ""},
            ]

            result = list_groups(geo_ctx=MagicMock())

        assert result == [
            GroupItem(id="role-uuid-1", label="ROLE_ADMIN"),
            GroupItem(id="role-uuid-2", label="ROLE_USER"),
        ]

    def test_given_filter_regex_when_listing_then_filters_labels(self) -> None:
        """Given a label filter regex, when listing, then returns only matching roles."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings(filter_regex="^ROLE_ADMIN"),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_roles.return_value = [
                {"id": "role-uuid-1", "name": "ROLE_ADMIN", "description": ""},
                {"id": "role-uuid-2", "name": "ROLE_USER", "description": ""},
            ]

            result = list_groups(geo_ctx=MagicMock())

        assert result == [GroupItem(id="role-uuid-1", label="ROLE_ADMIN")]

    def test_given_console_error_when_listing_then_raises_502(self) -> None:
        """Given a console API error, when listing, then raises HTTPException 502."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_roles.side_effect = Exception("connection refused")

            with pytest.raises(HTTPException) as exc_info:
                list_groups(geo_ctx=MagicMock())

        assert exc_info.value.status_code == 502

    def test_given_empty_roles_when_listing_then_returns_empty_list(self) -> None:
        """Given no roles from console, when listing, then returns empty list."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_roles.return_value = []

            result = list_groups(geo_ctx=MagicMock())

        assert result == []

    def test_given_roles_with_missing_fields_when_listing_then_skips_incomplete(self) -> None:
        """Given roles missing id or name, when listing, then skips those entries."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_roles.return_value = [
                {"id": "role-uuid-1", "name": "ROLE_ADMIN", "description": ""},
                {"id": "role-uuid-2"},  # missing name
                {"name": "ROLE_ORPHAN"},  # missing id
            ]

            result = list_groups(geo_ctx=MagicMock())

        assert result == [GroupItem(id="role-uuid-1", label="ROLE_ADMIN")]

    def test_given_invalid_filter_regex_when_listing_then_raises_400(self) -> None:
        """Given an invalid filter regex, when listing, then raises HTTPException 400."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings(filter_regex="[invalid"),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_roles.return_value = [{"id": "1", "name": "ROLE_X"}]

            with pytest.raises(HTTPException) as exc_info:
                list_groups(geo_ctx=MagicMock())

        assert exc_info.value.status_code == 400
