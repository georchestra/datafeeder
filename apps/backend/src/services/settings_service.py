"""Service for loading application settings from core Settings."""

import json
from functools import lru_cache
from typing import Any

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.task_executor import TaskExecutorType

logger = get_logger()


class SettingsService:
    """Service to manage frontend application settings from core Settings."""

    def __init__(self):
        """Initialize settings service using core Settings."""
        self._settings = get_settings()

    def get_all_settings(self) -> dict[str, Any]:
        """Get all settings as a dictionary.

        Returns:
            Dictionary of all configuration settings
        """
        try:
            projections = json.loads(self._settings.PROJECTIONS)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Failed to parse PROJECTIONS from settings: {e}")
            projections = []

        enabled_features = []
        if self._settings.TASK_EXECUTOR == TaskExecutorType.AIRFLOW:
            enabled_features.append("scheduling")
            enabled_features.append("events")
        if all([
            self._settings.POSTGRES_SOURCE_HOST,
            self._settings.POSTGRES_SOURCE_PORT,
            self._settings.POSTGRES_SOURCE_USER,
            self._settings.POSTGRES_SOURCE_PASSWORD,
            self._settings.POSTGRES_SOURCE_DB,
        ]):
            enabled_features.append("database_source")

        settings_dict: dict[str, Any] = {
            "projections": projections,
            "enabled_features": enabled_features,
        }
        return settings_dict


@lru_cache
def get_settings_service() -> SettingsService:
    """Get singleton instance of SettingsService.

    Uses lru_cache to ensure settings are only loaded once.

    Returns:
        SettingsService instance
    """
    logger.info("Initializing settings service")
    return SettingsService()
