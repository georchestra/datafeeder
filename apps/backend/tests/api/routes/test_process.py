"""Tests for the ingestion process route helpers."""

from src.api.routes.ingestion.process import (
    _is_geom_excluded,  # pyright: ignore[reportPrivateUsage]
)


class TestIsGeomExcluded:
    """Unit tests for _is_geom_excluded helper."""

    def test_returns_false_when_transformation_is_none(self) -> None:
        assert _is_geom_excluded(None) is False

    def test_returns_false_when_transformation_is_empty(self) -> None:
        assert _is_geom_excluded({}) is False

    def test_returns_false_when_columns_is_none(self) -> None:
        assert _is_geom_excluded({"columns": None}) is False

    def test_returns_false_when_columns_is_empty(self) -> None:
        assert _is_geom_excluded({"columns": []}) is False

    def test_returns_false_when_geom_not_excluded(self) -> None:
        transformation = {
            "columns": [
                {"original_name": "geom", "original_type": "text", "excluded": False},
                {"original_name": "name", "original_type": "text", "excluded": False},
            ]
        }
        assert _is_geom_excluded(transformation) is False

    def test_returns_true_when_geom_excluded(self) -> None:
        transformation = {
            "columns": [
                {"original_name": "geom", "original_type": "text", "excluded": True},
                {"original_name": "name", "original_type": "text", "excluded": False},
            ]
        }
        assert _is_geom_excluded(transformation) is True

    def test_returns_false_when_only_other_columns_excluded(self) -> None:
        transformation = {
            "columns": [
                {"original_name": "geom", "original_type": "text", "excluded": False},
                {"original_name": "secret", "original_type": "text", "excluded": True},
            ]
        }
        assert _is_geom_excluded(transformation) is False

    def test_returns_false_when_no_geom_column_in_config(self) -> None:
        transformation = {
            "columns": [
                {"original_name": "name", "original_type": "text", "excluded": False},
                {"original_name": "value", "original_type": "text", "excluded": True},
            ]
        }
        assert _is_geom_excluded(transformation) is False
