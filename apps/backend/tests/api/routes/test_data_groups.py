from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.routes.data_groups import list_groups
from src.api.routes.groups_common import GroupItem


class TestDataGroups:
    """Tests for the data groups route."""

    def _mock_settings(self, data_sync_mode: str = "ORG", filter_regex: str = "") -> MagicMock:
        mock_settings = MagicMock()
        mock_settings.CONSOLE_INTERNAL_URL = "http://console.example.com"
        mock_settings.DATA_SYNC_MODE = data_sync_mode
        mock_settings.DATA_GROUPS_LABEL_FILTER_REGEX = filter_regex
        return mock_settings

    def test_given_org_mode_when_listing_then_returns_organizations(self) -> None:
        """Given DATA_SYNC_MODE=ORG, when listing data groups, then returns organizations."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [
                {"id": "org-uuid-1", "name": "Camptocamp", "shortName": "C2C"},
                {"id": "org-uuid-2", "name": "GeoOrg", "shortName": "GEOORG"},
            ]

            result = list_groups(geo_ctx=MagicMock())

        assert result == [
            GroupItem(id="org-uuid-1", label="Camptocamp"),
            GroupItem(id="org-uuid-2", label="GeoOrg"),
        ]
        mock_console.get_all_organizations.assert_called_once()
        mock_console.get_all_roles.assert_not_called()

    def test_given_role_mode_when_listing_then_returns_roles(self) -> None:
        """Given DATA_SYNC_MODE=ROLE, when listing data groups, then returns roles."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings("ROLE"),
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
        mock_console.get_all_roles.assert_called_once()
        mock_console.get_all_organizations.assert_not_called()

    def test_given_filter_regex_when_listing_then_filters_labels(self) -> None:
        """Given a label filter regex, when listing, then returns only matching groups."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings("ORG", filter_regex="^Campto"),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [
                {"id": "org-uuid-1", "name": "Camptocamp", "shortName": "C2C"},
                {"id": "org-uuid-2", "name": "GeoOrg", "shortName": "GEOORG"},
            ]

            result = list_groups(geo_ctx=MagicMock())

        assert result == [GroupItem(id="org-uuid-1", label="Camptocamp")]

    def test_given_console_error_when_listing_then_raises_502(self) -> None:
        """Given a console API error, when listing, then raises HTTPException 502."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.side_effect = Exception("connection refused")

            with pytest.raises(HTTPException) as exc_info:
                list_groups(geo_ctx=MagicMock())

        assert exc_info.value.status_code == 502

    def test_given_empty_groups_when_listing_then_returns_empty_list(self) -> None:
        """Given no groups from console, when listing, then returns empty list."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = []

            result = list_groups(geo_ctx=MagicMock())

        assert result == []

    def test_given_items_with_missing_fields_when_listing_then_skips_incomplete(self) -> None:
        """Given items missing id or name, when listing, then skips those entries."""
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [
                {"id": "org-uuid-1", "name": "Camptocamp", "shortName": "C2C"},
                {"id": "org-uuid-2"},  # missing name
                {"name": "Orphan"},  # missing id
            ]

            result = list_groups(geo_ctx=MagicMock())

        assert result == [GroupItem(id="org-uuid-1", label="Camptocamp")]

    def test_given_invalid_filter_regex_when_listing_then_raises_502(self) -> None:
        """Given an invalid filter regex, when listing, then raises HTTPException 502.

        The regex compilation error (HTTPException 400) is raised inside the same
        try/except as the console calls, so it gets wrapped into a 502 - same behavior
        as the metadata groups route (see test_metadata_groups.py).
        """
        with (
            patch(
                "src.api.routes.data_groups.get_settings",
                return_value=self._mock_settings("ORG", filter_regex="[invalid"),
            ),
            patch("src.api.routes.data_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [{"id": "1", "name": "Org X"}]

            with pytest.raises(HTTPException) as exc_info:
                list_groups(geo_ctx=MagicMock())

        assert exc_info.value.status_code == 502
