"""Tests for the saved transformation in the staging metadata endpoints."""

from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from data_manipulation import PreviewResult
from fastapi import HTTPException

from src.api.routes.ingestion.staging import (
    edit_staging_metadata,
    get_staging_metadata,
    get_staging_preview,
)
from src.models.data_import import (
    ColumnConfig,
    ImportType,
    JoinConfig,
    StagingMetadata,
    StagingMetadataResponse,
)

JOIN = JoinConfig(
    integrity_link_id=uuid4(),
    source_column="insee",
    target_column="code_insee",
    columns=["nom", "population"],
)


def _mock_link(integrity_transformation: dict[str, Any] | None) -> MagicMock:
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
    return link


def _get_metadata(integrity_transformation: dict[str, Any] | None) -> StagingMetadataResponse:
    link = _mock_link(integrity_transformation)
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


class TestGetStagingMetadataJoin:
    def test_saved_join_is_returned(self) -> None:
        result = _get_metadata({"columns": None, "join": JOIN.model_dump(mode="json")})

        assert result.join == JOIN

    def test_no_join_when_none_saved(self) -> None:
        result = _get_metadata({"columns": None})

        assert result.join is None


def _edit_metadata(
    config: StagingMetadata, link: MagicMock, resolve: MagicMock | None = None
) -> None:
    with (
        patch(
            "src.api.routes.ingestion.staging.load_authorized_integrity_link",
            return_value=(link, MagicMock()),
        ),
        patch(
            "src.api.routes.ingestion.staging.resolve_join_target",
            resolve or MagicMock(),
        ),
        patch("src.api.routes.ingestion.staging.get_staging_metadata"),
    ):
        edit_staging_metadata(
            data_session=MagicMock(),
            datafeeder_session=MagicMock(),
            geo_ctx=MagicMock(),
            integrity_link_id=str(uuid4()),
            group_ids=[],
            config=config,
        )


class TestEditStagingMetadataJoin:
    def test_join_is_persisted(self) -> None:
        link = _mock_link(None)
        config = StagingMetadata(
            columns=[ColumnConfig(original_name="insee")], title="t", file_type=None, join=JOIN
        )

        _edit_metadata(config, link)

        assert link.integrity_transformation["join"] == JOIN.model_dump(mode="json")

    def test_saving_without_join_clears_previous_join(self) -> None:
        link = _mock_link({"columns": None, "join": JOIN.model_dump(mode="json")})
        config = StagingMetadata(
            columns=[ColumnConfig(original_name="insee")], title="t", file_type=None
        )

        _edit_metadata(config, link)

        assert link.integrity_transformation["join"] is None

    def test_unreadable_joined_dataset_is_rejected(self) -> None:
        link = _mock_link(None)
        config = StagingMetadata(
            columns=[ColumnConfig(original_name="insee")], title="t", file_type=None, join=JOIN
        )
        resolve = MagicMock(side_effect=HTTPException(status_code=403, detail="Forbidden"))

        with pytest.raises(HTTPException) as exc:
            _edit_metadata(config, link, resolve)

        assert exc.value.status_code == 403
        assert resolve.call_args.args[0] == JOIN
        assert link.integrity_transformation is None

    def test_join_with_itself_is_rejected(self) -> None:
        link = _mock_link(None)
        link.id = JOIN.integrity_link_id
        config = StagingMetadata(
            columns=[ColumnConfig(original_name="insee")], title="t", file_type=None, join=JOIN
        )

        with pytest.raises(HTTPException) as exc:
            _edit_metadata(config, link)

        assert exc.value.status_code == 422
        assert link.integrity_transformation is None


GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [1, 2]}, "properties": {}}
    ],
}


def _preview(
    integrity_transformation: dict[str, Any], include_excluded: bool = False
) -> tuple[Any, MagicMock]:
    """Run get_staging_preview; return the response and the read_transformed_preview mock."""
    read = MagicMock(
        return_value=PreviewResult(
            rows=[{"geom": "POINT(1 2)"}], geojson=GEOJSON, is_geographic=True
        )
    )
    with (
        patch(
            "src.api.routes.ingestion.staging.load_authorized_integrity_link",
            return_value=(_mock_link(integrity_transformation), MagicMock()),
        ),
        patch("src.api.routes.ingestion.staging.resolve_join_target"),
        patch("src.api.routes.ingestion.staging.read_transformed_preview", read),
    ):
        response = get_staging_preview(
            data_session=MagicMock(),
            datafeeder_session=MagicMock(),
            geo_ctx=MagicMock(),
            integrity_link_id=str(uuid4()),
            group_ids=[],
            limit=10,
            raw=False,
            include_excluded=include_excluded,
        )
    return response, read


def _excluded_geom(join_columns: list[str]) -> dict[str, Any]:
    join = JOIN.model_copy(update={"columns": join_columns})
    return {
        "columns": [
            {"original_name": "insee"},
            {"original_name": "geom", "excluded": True},
        ],
        "join": join.model_dump(mode="json"),
    }


class TestStagingPreviewJoinedGeom:
    def test_excluded_staging_geom_hides_the_map(self) -> None:
        response, _ = _preview(_excluded_geom(["nom"]))

        assert response.is_geographic is False
        assert response.geojson is None

    def test_joined_geom_replacing_excluded_staging_geom_is_mapped(self) -> None:
        response, _ = _preview(_excluded_geom(["nom", "geom"]))

        assert response.is_geographic is True
        assert response.geojson is not None

    def test_include_excluded_keeps_staging_geom_excluded_when_geom_is_joined(self) -> None:
        _, read = _preview(_excluded_geom(["nom", "geom"]), include_excluded=True)

        config = read.call_args.args[2]
        excluded = {col.original_name: col.excluded for col in config.columns}
        assert excluded == {"insee": False, "geom": True}

    def test_include_excluded_includes_staging_geom_without_joined_geom(self) -> None:
        _, read = _preview(_excluded_geom(["nom"]), include_excluded=True)

        config = read.call_args.args[2]
        assert all(not col.excluded for col in config.columns)
