"""Tests for SettingsService."""

import json
from unittest.mock import MagicMock, patch

from src.services.settings_service import SettingsService, get_settings_service


class TestSettingsService:
    """Test suite for SettingsService."""

    @patch("src.services.settings_service.get_settings")
    def test_get_all_settings_with_valid_projections(self, mock_get_settings: MagicMock) -> None:
        """Test that get_all_settings returns projections when valid JSON is provided."""
        # Arrange
        mock_settings = MagicMock()
        projections_data = [
            {"value": "EPSG:4326", "label": "WGS 84"},
            {"value": "EPSG:3857", "label": "Web Mercator"},
            {"value": "EPSG:2154", "label": "Lambert 93"},
        ]
        mock_settings.PROJECTIONS = json.dumps(projections_data)
        mock_get_settings.return_value = mock_settings

        # Act
        service = SettingsService()
        result = service.get_all_settings()

        # Assert
        assert "projections" in result
        assert result["projections"] == projections_data
        assert len(result["projections"]) == 3
        assert result["projections"][2]["value"] == "EPSG:2154"
        assert result["projections"][2]["label"] == "Lambert 93"

    @patch("src.services.settings_service.get_settings")
    def test_get_all_settings_with_empty_projections(self, mock_get_settings: MagicMock) -> None:
        """Test that get_all_settings returns empty list when PROJECTIONS is empty JSON array."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.PROJECTIONS = "[]"
        mock_get_settings.return_value = mock_settings

        # Act
        service = SettingsService()
        result = service.get_all_settings()

        # Assert
        assert "projections" in result
        assert result["projections"] == []

    @patch("src.services.settings_service.get_settings")
    def test_get_all_settings_with_invalid_json(self, mock_get_settings: MagicMock) -> None:
        """Test that get_all_settings returns empty list when JSON is invalid."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.PROJECTIONS = "invalid json"
        mock_get_settings.return_value = mock_settings

        # Act
        service = SettingsService()
        result = service.get_all_settings()

        # Assert
        assert "projections" in result
        assert result["projections"] == []

    @patch("src.services.settings_service.get_settings")
    def test_get_all_settings_with_missing_attribute(self, mock_get_settings: MagicMock) -> None:
        """Test that get_all_settings handles missing PROJECTIONS attribute gracefully."""
        # Arrange
        mock_settings = MagicMock()
        del mock_settings.PROJECTIONS  # Simulate missing attribute
        mock_get_settings.return_value = mock_settings

        # Act
        service = SettingsService()
        result = service.get_all_settings()

        # Assert
        assert "projections" in result
        assert result["projections"] == []

    @patch("src.services.settings_service.get_settings")
    def test_get_settings_service_singleton(self, mock_get_settings: MagicMock) -> None:
        """Test that get_settings_service returns the same instance (singleton pattern)."""
        # Arrange
        mock_settings = MagicMock()
        mock_settings.PROJECTIONS = "[]"
        mock_get_settings.return_value = mock_settings

        # Clear the lru_cache to ensure clean test
        get_settings_service.cache_clear()

        # Act
        service1 = get_settings_service()
        service2 = get_settings_service()

        # Assert
        assert service1 is service2
        # get_settings should only be called once due to singleton
        assert mock_get_settings.call_count == 1

    @patch("src.services.settings_service.get_settings")
    def test_database_source_feature_flag_present_when_source_databases_set(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test that database_source is in enabled_features when SOURCE_DATABASES has entries."""
        mock_settings = MagicMock()
        mock_settings.PROJECTIONS = "[]"
        mock_settings.SOURCE_DATABASES = {"SOURCE_DB_1": "postgresql://user:pass@host:5432/db"}
        mock_get_settings.return_value = mock_settings

        service = SettingsService()
        result = service.get_all_settings()

        assert "database_source" in result["enabled_features"]

    @patch("src.services.settings_service.get_settings")
    def test_database_source_feature_flag_absent_when_source_databases_empty(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test that database_source is NOT in enabled_features when SOURCE_DATABASES is empty."""
        mock_settings = MagicMock()
        mock_settings.PROJECTIONS = "[]"
        mock_settings.SOURCE_DATABASES = {}
        mock_get_settings.return_value = mock_settings

        service = SettingsService()
        result = service.get_all_settings()

        assert "database_source" not in result["enabled_features"]

    @patch("src.services.settings_service.get_settings")
    def test_database_source_feature_flag_present_with_multiple_databases(
        self, mock_get_settings: MagicMock
    ) -> None:
        """Test that database_source is in enabled_features when SOURCE_DATABASES has multiple entries."""
        mock_settings = MagicMock()
        mock_settings.PROJECTIONS = "[]"
        mock_settings.SOURCE_DATABASES = {
            "SOURCE_DB_1": "postgresql://user:pass@host1:5432/db1",
            "SOURCE_DB_2": "postgresql://user:pass@host2:5432/db2",
        }
        mock_get_settings.return_value = mock_settings

        service = SettingsService()
        result = service.get_all_settings()

        assert "database_source" in result["enabled_features"]

    @patch("src.services.settings_service.get_settings")
    def test_projections_structure(self, mock_get_settings: MagicMock) -> None:
        """Test that projections have the expected structure with value and label."""
        # Arrange
        mock_settings = MagicMock()
        projections_data = [
            {"value": "EPSG:4326", "label": "WGS 84"},
            {"value": "EPSG:2154", "label": "Lambert 93"},
        ]
        mock_settings.PROJECTIONS = json.dumps(projections_data)
        mock_get_settings.return_value = mock_settings

        # Act
        service = SettingsService()
        result = service.get_all_settings()

        # Assert
        projections = result["projections"]
        assert all("value" in proj for proj in projections)
        assert all("label" in proj for proj in projections)
        assert all(isinstance(proj["value"], str) for proj in projections)
        assert all(isinstance(proj["label"], str) for proj in projections)
