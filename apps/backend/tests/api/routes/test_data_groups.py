from unittest.mock import Mock, patch

from src.api.routes.data_groups import list_groups


class TestDataGroups:
    """Tests for the data groups route."""

    def test_given_settings_when_listing_then_delegates_to_fetch_groups(self) -> None:
        """Given DATA_* settings, when listing groups, then delegates to fetch_groups with correct params."""
        mock_settings = Mock()
        mock_settings.DATA_FETCH_GROUPS_URL = "http://example.com/roles"
        mock_settings.DATA_GROUPS_IDENTIFIER = "name"
        mock_settings.DATA_GROUPS_LABEL = "name"
        mock_settings.DATA_FETCH_GROUPS_USERNAME = "admin"
        mock_settings.DATA_FETCH_GROUPS_PASSWORD = "secret"

        with (
            patch("src.api.routes.data_groups.get_settings", return_value=mock_settings),
            patch("src.api.routes.data_groups.fetch_groups", return_value=[]) as mock_fetch,
        ):
            result = list_groups(geo_ctx=Mock())

        mock_fetch.assert_called_once_with(
            url="http://example.com/roles",
            id_field="name",
            label_field="name",
            username="admin",
            password="secret",
        )
        assert result == []
