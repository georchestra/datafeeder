"""Tests for schema helpers in core config."""

from unittest.mock import patch

from src.core.config import is_shared_schema


class TestIsSharedSchema:
    def test_staging_schema_is_shared(self) -> None:
        assert is_shared_schema("staging")

    def test_default_data_schema_is_shared(self) -> None:
        assert is_shared_schema("data")

    def test_org_schema_is_not_shared(self) -> None:
        assert not is_shared_schema("myorg")

    def test_follows_configured_staging_schema(self) -> None:
        """The guard tracks get_staging_schema, not a hardcoded literal."""
        with patch("src.core.config.get_staging_schema", return_value="staging_v2"):
            assert is_shared_schema("staging_v2")
            assert not is_shared_schema("staging")
