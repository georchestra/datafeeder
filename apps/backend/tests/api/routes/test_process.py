"""Tests for the ingestion process route helpers."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from data_manipulation.models import IntegrityTransformation

from src.api.routes.ingestion.process import (
    _has_xy_projection,  # pyright: ignore[reportPrivateUsage]
    _is_geom_excluded,  # pyright: ignore[reportPrivateUsage]
    _normalize_title,  # pyright: ignore[reportPrivateUsage]
    dag_success_callback,
)
from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink


def _t(payload: dict[str, object]) -> IntegrityTransformation:
    return IntegrityTransformation.model_validate(payload)


class TestIsGeomExcluded:
    """Unit tests for _is_geom_excluded helper."""

    def test_returns_false_when_transformation_is_none(self) -> None:
        assert _is_geom_excluded(None) is False

    def test_returns_false_when_transformation_is_empty(self) -> None:
        assert _is_geom_excluded(_t({})) is False

    def test_returns_false_when_columns_is_none(self) -> None:
        assert _is_geom_excluded(_t({"columns": None})) is False

    def test_returns_false_when_columns_is_empty(self) -> None:
        assert _is_geom_excluded(_t({"columns": []})) is False

    def test_returns_false_when_geom_not_excluded(self) -> None:
        transformation = _t(
            {
                "columns": [
                    {"original_name": "geom", "original_type": "text", "excluded": False},
                    {"original_name": "name", "original_type": "text", "excluded": False},
                ]
            }
        )
        assert _is_geom_excluded(transformation) is False

    def test_returns_true_when_geom_excluded(self) -> None:
        transformation = _t(
            {
                "columns": [
                    {"original_name": "geom", "original_type": "text", "excluded": True},
                    {"original_name": "name", "original_type": "text", "excluded": False},
                ]
            }
        )
        assert _is_geom_excluded(transformation) is True

    def test_returns_false_when_only_other_columns_excluded(self) -> None:
        transformation = _t(
            {
                "columns": [
                    {"original_name": "geom", "original_type": "text", "excluded": False},
                    {"original_name": "secret", "original_type": "text", "excluded": True},
                ]
            }
        )
        assert _is_geom_excluded(transformation) is False

    def test_returns_false_when_no_geom_column_in_config(self) -> None:
        transformation = _t(
            {
                "columns": [
                    {"original_name": "name", "original_type": "text", "excluded": False},
                    {"original_name": "value", "original_type": "text", "excluded": True},
                ]
            }
        )
        assert _is_geom_excluded(transformation) is False


class TestHasXyProjection:
    """Unit tests for _has_xy_projection helper."""

    def test_returns_false_when_transformation_is_none(self) -> None:
        assert _has_xy_projection(None) is False

    def test_returns_false_when_no_force_projection(self) -> None:
        assert _has_xy_projection(_t({})) is False

    def test_returns_true_when_x_and_y_columns_set(self) -> None:
        transformation = _t(
            {"force_projection": {"type": "EPSG:3857", "x_column": "X", "y_column": "Y"}}
        )
        assert _has_xy_projection(transformation) is True

    def test_returns_false_when_only_x_column_set(self) -> None:
        transformation = _t(
            {"force_projection": {"type": "EPSG:3857", "x_column": "X", "y_column": None}}
        )
        assert _has_xy_projection(transformation) is False

    def test_returns_false_when_only_y_column_set(self) -> None:
        transformation = _t(
            {"force_projection": {"type": "EPSG:3857", "x_column": None, "y_column": "Y"}}
        )
        assert _has_xy_projection(transformation) is False

    def test_returns_false_when_force_projection_is_empty(self) -> None:
        transformation = _t({"force_projection": {"type": "EPSG:3857"}})
        assert _has_xy_projection(transformation) is False


class TestNormalizeTitle:
    """Unit tests for _normalize_title helper."""

    def test_none_returns_fallback(self) -> None:
        assert _normalize_title(None) == "No title"

    def test_empty_string_returns_fallback(self) -> None:
        assert _normalize_title("") == "No title"

    def test_whitespace_only_returns_fallback(self) -> None:
        assert _normalize_title("   ") == "No title"

    def test_custom_fallback(self) -> None:
        assert _normalize_title(None, fallback="Untitled") == "Untitled"

    def test_normal_title_unchanged(self) -> None:
        assert _normalize_title("My Dataset") == "My Dataset"

    def test_strips_surrounding_whitespace(self) -> None:
        assert _normalize_title("  My Dataset  ") == "My Dataset"


def _make_integrity_link_with_metadata() -> IntegrityLink:
    link = IntegrityLink(
        id=uuid4(),
        integrity_owner="testuser",
        integrity_organization="testorg",
        source_import_type=ImportType.URL,
        staging_table_name="staging_test",
    )
    link.metadata_id = str(link.id)
    return link


def _make_mock_session(link: IntegrityLink) -> MagicMock:
    session = MagicMock()
    session.get.return_value = link
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session


def _make_mock_geoserver() -> AsyncMock:
    geoserver = AsyncMock()
    geoserver.workspace_exists.return_value = True
    geoserver.datastore_exists.return_value = True
    geoserver.create_layer = AsyncMock()
    return geoserver


@pytest.mark.asyncio
class TestDagSuccessCallbackRevisionDate:
    """Tests for the revision date update logic in dag_success_callback."""

    @patch("src.api.routes.ingestion.process.MetadataService")
    @patch("src.api.routes.ingestion.process.Table")
    @patch("src.api.routes.ingestion.process.create_schema")
    async def test_calls_update_revision_date_when_metadata_id_set(
        self,
        mock_create_schema: MagicMock,
        mock_table_cls: MagicMock,
        mock_metadata_service_cls: MagicMock,
    ) -> None:
        """When metadata_id is set, update_revision_date() must be called."""
        link = _make_integrity_link_with_metadata()
        mock_table_cls.return_value.c = {}  # no geometry column

        await dag_success_callback(
            datafeeder_session=_make_mock_session(link),
            geoserver_service=_make_mock_geoserver(),
            integrity_link_id=str(link.id),
            final_table_name="final_test",
        )

        mock_metadata_service_cls.return_value.update_revision_date.assert_called_once()
        call_args = mock_metadata_service_cls.return_value.update_revision_date.call_args
        assert call_args[0][0] == str(link.id)
        assert isinstance(call_args[0][1], datetime)

    @patch("src.api.routes.ingestion.process.MetadataService")
    @patch("src.api.routes.ingestion.process.Table")
    @patch("src.api.routes.ingestion.process.create_schema")
    async def test_skips_update_when_metadata_id_is_none(
        self,
        mock_create_schema: MagicMock,
        mock_table_cls: MagicMock,
        mock_metadata_service_cls: MagicMock,
    ) -> None:
        """When metadata_id is None, update_revision_date() must not be called."""
        link = IntegrityLink(
            id=uuid4(),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
        )
        mock_table_cls.return_value.c = {}

        await dag_success_callback(
            datafeeder_session=_make_mock_session(link),
            geoserver_service=_make_mock_geoserver(),
            integrity_link_id=str(link.id),
            final_table_name="final_test",
        )

        mock_metadata_service_cls.return_value.update_revision_date.assert_not_called()

    @patch("src.api.routes.ingestion.process.MetadataService")
    @patch("src.api.routes.ingestion.process.Table")
    @patch("src.api.routes.ingestion.process.create_schema")
    async def test_soft_failure_does_not_raise(
        self,
        mock_create_schema: MagicMock,
        mock_table_cls: MagicMock,
        mock_metadata_service_cls: MagicMock,
    ) -> None:
        """When update_revision_date() raises, the callback must not propagate the error."""
        link = _make_integrity_link_with_metadata()
        mock_table_cls.return_value.c = {}
        mock_metadata_service_cls.return_value.update_revision_date.side_effect = RuntimeError(
            "GeoNetwork unavailable"
        )

        # Should not raise
        await dag_success_callback(
            datafeeder_session=_make_mock_session(link),
            geoserver_service=_make_mock_geoserver(),
            integrity_link_id=str(link.id),
            final_table_name="final_test",
        )
