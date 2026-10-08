"""Tests for the saved transformation parsing in get_staging_metadata."""

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.api.routes.ingestion.staging import get_staging_metadata
from src.models.data_import import ImportType, StagingMetadataResponse


def _get_metadata(integrity_transformation: dict[str, Any] | None) -> StagingMetadataResponse:
    link = MagicMock()
    link.integrity_title = "My dataset"
    link.source_file_name = None
    link.source_file_type = None
    link.source_import_type = ImportType.FILE
    link.source_url = None
    link.source_layer = None
    link.final_table_name = None
    link.staging_table_name = "staging_table"
    link.integrity_transformation = integrity_transformation
    data_session = MagicMock()
    data_session.scalar.return_value = 0

    with (
        patch(
            "src.api.routes.ingestion.staging.load_authorized_integrity_link",
            return_value=(link, MagicMock()),
        ),
        patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging"),
        patch("src.api.routes.ingestion.staging.select"),
        patch("src.api.routes.ingestion.staging.Table"),
        patch("src.api.routes.ingestion.staging._resolve_columns", return_value=[]),
        patch("src.api.routes.ingestion.staging._detect_original_projection", return_value=None),
    ):
        return get_staging_metadata(
            data_session=data_session,
            datafeeder_session=MagicMock(),
            geo_ctx=MagicMock(),
            integrity_link_id=str(uuid4()),
            group_ids=[],
        )


class TestGetStagingMetadataForceProjection:
    def test_saved_force_projection_is_returned_without_saved_columns(self) -> None:
        saved_projection = {"type": "EPSG:2154", "x_column": "x", "y_column": "y"}

        result = _get_metadata({"columns": None, "force_projection": saved_projection})

        assert result.force_projection is not None
        assert result.force_projection.model_dump() == saved_projection

    def test_no_force_projection_when_no_transformation_saved(self) -> None:
        result = _get_metadata(None)

        assert result.force_projection is None

    def test_malformed_transformation_falls_back_to_no_force_projection(self) -> None:
        malformed: dict[str, Any] = {
            "columns": [{"new_name": "missing original_name"}],
            "force_projection": {},
        }

        result = _get_metadata(malformed)

        assert result.force_projection is None
