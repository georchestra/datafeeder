from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from src.api.routes.groups_common import GroupItem
from src.api.routes.metadata_groups import list_groups


class TestMetadataGroups:
    """Tests for the metadata groups route."""

    def _mock_settings(self, gn_sync_mode: str = "ORG", filter_regex: str = "") -> MagicMock:
        mock_settings = MagicMock()
        mock_settings.CONSOLE_URL = "http://console.example.com"
        mock_settings.GN_SYNC_MODE = gn_sync_mode
        mock_settings.METADATA_GROUPS_LABEL_FILTER_REGEX = filter_regex
        return mock_settings

    def test_given_org_mode_when_listing_then_returns_organizations(self) -> None:
        """Given GN_SYNC_MODE=ORG, when listing metadata groups, then returns organizations."""
        with (
            patch(
                "src.api.routes.metadata_groups.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.metadata_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [
                {"id": "uuid-1", "name": "Camptocamp"},
                {"id": "uuid-2", "name": "GeoOrg"},
            ]

            result = list_groups(geo_ctx=MagicMock())

        assert result == [
            GroupItem(id="uuid-1", label="Camptocamp"),
            GroupItem(id="uuid-2", label="GeoOrg"),
        ]
        mock_console.get_all_organizations.assert_called_once()
        mock_console.get_all_roles.assert_not_called()

    def test_given_role_mode_when_listing_then_returns_roles(self) -> None:
        """Given GN_SYNC_MODE=ROLE, when listing metadata groups, then returns roles."""
        with (
            patch(
                "src.api.routes.metadata_groups.get_settings",
                return_value=self._mock_settings("ROLE"),
            ),
            patch("src.api.routes.metadata_groups.ConsoleService") as mock_console_cls,
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
                "src.api.routes.metadata_groups.get_settings",
                return_value=self._mock_settings("ORG", filter_regex="^Campto"),
            ),
            patch("src.api.routes.metadata_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [
                {"id": "uuid-1", "name": "Camptocamp", "description": ""},
                {"id": "uuid-2", "name": "GeoOrg", "description": ""},
            ]

            result = list_groups(geo_ctx=MagicMock())

        assert result == [GroupItem(id="uuid-1", label="Camptocamp")]

    def test_given_console_error_when_listing_then_raises_502(self) -> None:
        """Given a console API error, when listing, then raises HTTPException 502."""
        with (
            patch(
                "src.api.routes.metadata_groups.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.metadata_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.side_effect = Exception("connection refused")

            with pytest.raises(HTTPException) as exc_info:
                list_groups(geo_ctx=MagicMock())

        assert exc_info.value.status_code == 502

    def test_given_items_with_missing_fields_when_listing_then_skips_incomplete(self) -> None:
        """Given orgs missing id or name, when listing, then skips those entries."""
        with (
            patch(
                "src.api.routes.metadata_groups.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.metadata_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [
                {"id": "uuid-1", "name": "Camptocamp"},
                {"id": "uuid-2"},  # missing name
                {"name": "Orphan"},  # missing id
            ]

            result = list_groups(geo_ctx=MagicMock())

        assert result == [GroupItem(id="uuid-1", label="Camptocamp")]

    def test_given_invalid_filter_regex_when_listing_then_raises_502(self) -> None:
        """Given an invalid filter regex, when listing, then raises HTTPException 502."""
        with (
            patch(
                "src.api.routes.metadata_groups.get_settings",
                return_value=self._mock_settings("ORG", filter_regex="[invalid"),
            ),
            patch("src.api.routes.metadata_groups.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [{"id": "1", "name": "Org X"}]

            with pytest.raises(HTTPException) as exc_info:
                list_groups(geo_ctx=MagicMock())

        assert exc_info.value.status_code == 502
