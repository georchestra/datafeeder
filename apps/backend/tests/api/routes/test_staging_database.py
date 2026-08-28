"""Tests for database source type in staging endpoints."""

from collections.abc import Generator
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from data_manipulation.constants import DB_URI_PREFIX
from data_manipulation.validators import validate_schema_name, validate_table_name
from fastapi import HTTPException

from src.api.routes.ingestion.staging import (
    _process_import_source,  # pyright: ignore[reportPrivateUsage]
    dag_success_callback,
    edit_staging,
    get_staging_metadata,
)
from src.models.data_import import FileType, ImportType, StagingMetadataResponse


class TestDbIdentifierValidation:
    """Test schema/table validation via data_manipulation.validators."""

    @pytest.mark.parametrize(
        "name",
        [
            "public",
            "my_data_table",
            "a",
            "schema123",
            "a" * 63,
        ],
    )
    def test_valid_schema_names_accepted(self, name: str) -> None:
        assert validate_schema_name(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "public",
            "my_data_table",
            "a",
            "schema123",
            "a" * 63,
        ],
    )
    def test_valid_table_names_accepted(self, name: str) -> None:
        assert validate_table_name(name) == name

    @pytest.mark.parametrize(
        "name",
        [
            "Public",
            "123table",
            "my-schema",
            "_leading_underscore",
            "a" * 64,
            "table; DROP TABLE",
            "schema.table",
        ],
    )
    def test_invalid_names_rejected(self, name: str) -> None:
        with pytest.raises(ValueError):
            validate_schema_name(name)

    def test_empty_name_rejected(self) -> None:
        with pytest.raises(ValueError):
            validate_schema_name("")


class TestProcessImportSourceDatabase:
    """Test _process_import_source for ImportType.DATABASE."""

    @pytest.mark.asyncio
    @patch("src.api.routes.ingestion.staging.table_exists", return_value=True)
    @patch("src.api.routes.ingestion.staging.schema_exists", return_value=True)
    @patch("src.api.routes.ingestion.staging.source_db_key", new="SOURCE_DB_1")
    @patch("src.api.routes.ingestion.staging.source_engine")
    async def test_valid_database_source(
        self,
        mock_engine: MagicMock,
        mock_schema: MagicMock,
        mock_table: MagicMock,
    ) -> None:
        result = await _process_import_source(
            type=ImportType.DATABASE,
            db_schema="geo",
            db_table="rivers",
        )
        assert result.source == "db://SOURCE_DB_1/geo/rivers"
        assert result.url == "db://SOURCE_DB_1/geo/rivers"
        assert result.source_file_name is None
        assert result.source_file_type is None
        assert result.auth_enabled is False

    @pytest.mark.asyncio
    @patch("src.api.routes.ingestion.staging.schema_exists", return_value=False)
    @patch("src.api.routes.ingestion.staging.source_db_key", new="SOURCE_DB_1")
    @patch("src.api.routes.ingestion.staging.source_engine")
    async def test_nonexistent_schema_returns_422(
        self,
        mock_engine: MagicMock,
        mock_schema: MagicMock,
    ) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="nonexistent",
                db_table="rivers",
            )
        assert exc_info.value.status_code == 422
        assert "Schema 'nonexistent' not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("src.api.routes.ingestion.staging.table_exists", return_value=False)
    @patch("src.api.routes.ingestion.staging.schema_exists", return_value=True)
    @patch("src.api.routes.ingestion.staging.source_db_key", new="SOURCE_DB_1")
    @patch("src.api.routes.ingestion.staging.source_engine")
    async def test_nonexistent_table_returns_422(
        self,
        mock_engine: MagicMock,
        mock_schema: MagicMock,
        mock_table: MagicMock,
    ) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="geo",
                db_table="nonexistent",
            )
        assert exc_info.value.status_code == 422
        assert "Table 'nonexistent' not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_missing_schema_returns_400(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema=None,
                db_table="rivers",
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_table_returns_400(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="geo",
                db_table=None,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_schema_returns_422(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="Invalid",
                db_table="rivers",
            )
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_table_returns_422(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="geo",
                db_table="123bad",
            )
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_schema_returns_400(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.DATABASE,
                db_schema="",
                db_table="rivers",
            )
        assert exc_info.value.status_code == 400


class TestDagSuccessCallbackDeleteGuard:
    """Test that delete_temp_file is not called for database sources."""

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_delete_not_called_for_database_source(self, mock_delete: MagicMock) -> None:
        """Verify delete_temp_file is skipped when source_import_type is DATABASE."""
        mock_integrity_link = MagicMock()
        mock_integrity_link.source_url = "db://geo/rivers"
        mock_integrity_link.source_import_type = ImportType.DATABASE
        mock_integrity_link.created_at = datetime.now(timezone.utc)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_integrity_link

        dag_success_callback(session=mock_session, integrity_link_id=str(uuid4()))

        mock_delete.assert_not_called()

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_delete_called_for_file_source(self, mock_delete: MagicMock) -> None:
        """Verify delete_temp_file is called when source_import_type is FILE."""
        mock_integrity_link = MagicMock()
        mock_integrity_link.source_url = "/tmp/somefile.csv"
        mock_integrity_link.source_import_type = ImportType.FILE
        mock_integrity_link.created_at = datetime.now(timezone.utc)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_integrity_link

        dag_success_callback(session=mock_session, integrity_link_id=str(uuid4()))

        mock_delete.assert_called_once_with("/tmp/somefile.csv")


@pytest.fixture
def staging_metadata_deps() -> Generator[SimpleNamespace, None, None]:
    """Patch every dependency get_staging_metadata needs besides the IntegrityLink
    and staging table content, which each test configures itself via .load and
    .table."""
    with (
        patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging"),
        patch("src.api.routes.ingestion.staging.select"),
        patch("src.api.routes.ingestion.staging.Table") as mock_table,
        patch("src.api.routes.ingestion.staging._resolve_columns") as mock_resolve_cols,
        patch("src.api.routes.ingestion.staging._detect_original_projection") as mock_detect_proj,
        patch("src.api.routes.ingestion.staging.load_authorized_integrity_link") as mock_load,
    ):
        mock_resolve_cols.return_value = ([], None)
        mock_detect_proj.return_value = None
        yield SimpleNamespace(load=mock_load, table=mock_table)


def _call_get_staging_metadata() -> StagingMetadataResponse:
    data_session = MagicMock()
    data_session.scalar.return_value = 0
    return get_staging_metadata(
        data_session=data_session,
        datafeeder_session=MagicMock(),
        geo_ctx=MagicMock(),
        integrity_link_id=str(uuid4()),
        group_ids=[],
    )


class TestGetStagingMetadataTitleFallback:
    """Test title fallback logic in get_staging_metadata for database sources."""

    @patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging")
    @patch("src.api.routes.ingestion.staging.select")
    @patch("src.api.routes.ingestion.staging.Table")
    @patch("src.api.routes.ingestion.staging._resolve_columns")
    @patch("src.api.routes.ingestion.staging._detect_original_projection")
    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_title_falls_back_to_table_name_from_source_url(
        self,
        mock_load: MagicMock,
        mock_detect_proj: MagicMock,
        mock_resolve_cols: MagicMock,
        mock_table: MagicMock,
        mock_select: MagicMock,
        mock_get_schema: MagicMock,
    ) -> None:
        """Title is the table name parsed from db://{schema}/{table} when no custom title is set."""
        mock_link = MagicMock()
        mock_link.integrity_title = None
        mock_link.source_file_name = None
        mock_link.source_file_type = None
        mock_link.source_import_type = ImportType.DATABASE
        mock_link.source_url = "db://SOURCE_DB_1/geo/parcels"
        mock_link.integrity_transformation = None
        mock_link.final_table_name = None
        mock_load.return_value = (mock_link, MagicMock())
        mock_resolve_cols.return_value = ([], None)
        mock_detect_proj.return_value = None

        data_session = MagicMock()
        data_session.scalar.return_value = 0

        result = get_staging_metadata(
            data_session=data_session,
            datafeeder_session=MagicMock(),
            geo_ctx=MagicMock(),
            integrity_link_id=str(uuid4()),
            group_ids=[],
        )

        assert result.title == "parcels"

    @patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging")
    @patch("src.api.routes.ingestion.staging.select")
    @patch("src.api.routes.ingestion.staging.Table")
    @patch("src.api.routes.ingestion.staging._resolve_columns")
    @patch("src.api.routes.ingestion.staging._detect_original_projection")
    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_custom_title_overrides_table_name(
        self,
        mock_load: MagicMock,
        mock_detect_proj: MagicMock,
        mock_resolve_cols: MagicMock,
        mock_table: MagicMock,
        mock_select: MagicMock,
        mock_get_schema: MagicMock,
    ) -> None:
        """integrity_title takes precedence over table name derived from source_url."""
        mock_link = MagicMock()
        mock_link.integrity_title = "Parcelles cadastrales"
        mock_link.source_file_name = None
        mock_link.source_file_type = None
        mock_link.source_import_type = ImportType.DATABASE
        mock_link.source_url = "db://SOURCE_DB_1/geo/parcels"
        mock_link.integrity_transformation = None
        mock_link.final_table_name = None
        mock_load.return_value = (mock_link, MagicMock())
        mock_resolve_cols.return_value = ([], None)
        mock_detect_proj.return_value = None

        data_session = MagicMock()
        data_session.scalar.return_value = 0

        result = get_staging_metadata(
            data_session=data_session,
            datafeeder_session=MagicMock(),
            geo_ctx=MagicMock(),
            integrity_link_id=str(uuid4()),
            group_ids=[],
        )

        assert result.title == "Parcelles cadastrales"

    @patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging")
    @patch("src.api.routes.ingestion.staging.select")
    @patch("src.api.routes.ingestion.staging.Table")
    @patch("src.api.routes.ingestion.staging._resolve_columns")
    @patch("src.api.routes.ingestion.staging._detect_original_projection")
    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_title_strips_extension_from_source_file_name(
        self,
        mock_load: MagicMock,
        mock_detect_proj: MagicMock,
        mock_resolve_cols: MagicMock,
        mock_table: MagicMock,
        mock_select: MagicMock,
        mock_get_schema: MagicMock,
    ) -> None:
        """source_file_name extension is stripped when used as title fallback."""
        mock_link = MagicMock()
        mock_link.integrity_title = None
        mock_link.source_file_name = "data.csv"
        mock_link.source_file_type = None
        mock_link.source_import_type = ImportType.URL
        mock_link.source_url = None
        mock_link.integrity_transformation = None
        mock_link.final_table_name = None
        mock_load.return_value = (mock_link, MagicMock())
        mock_resolve_cols.return_value = ([], None)
        mock_detect_proj.return_value = None

        data_session = MagicMock()
        data_session.scalar.return_value = 0

        result = get_staging_metadata(
            data_session=data_session,
            datafeeder_session=MagicMock(),
            geo_ctx=MagicMock(),
            integrity_link_id=str(uuid4()),
            group_ids=[],
        )

        assert result.title == "data"

    @patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging")
    @patch("src.api.routes.ingestion.staging.select")
    @patch("src.api.routes.ingestion.staging.Table")
    @patch("src.api.routes.ingestion.staging._resolve_columns")
    @patch("src.api.routes.ingestion.staging._detect_original_projection")
    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_title_preserves_hidden_file_name(
        self,
        mock_load: MagicMock,
        mock_detect_proj: MagicMock,
        mock_resolve_cols: MagicMock,
        mock_table: MagicMock,
        mock_select: MagicMock,
        mock_get_schema: MagicMock,
    ) -> None:
        """Hidden-file names (leading dot) are kept as-is without stripping the extension."""
        mock_link = MagicMock()
        mock_link.integrity_title = None
        mock_link.source_file_name = ".hidden.csv"
        mock_link.source_file_type = None
        mock_link.source_import_type = ImportType.URL
        mock_link.source_url = None
        mock_link.integrity_transformation = None
        mock_link.final_table_name = None
        mock_load.return_value = (mock_link, MagicMock())
        mock_resolve_cols.return_value = ([], None)
        mock_detect_proj.return_value = None

        data_session = MagicMock()
        data_session.scalar.return_value = 0

        result = get_staging_metadata(
            data_session=data_session,
            datafeeder_session=MagicMock(),
            geo_ctx=MagicMock(),
            integrity_link_id=str(uuid4()),
            group_ids=[],
        )

        assert result.title == ".hidden"


class TestGetStagingMetadataFileTypeOverride:
    """The extension-based file_type guess is corrected against the actual staging
    table for the two ambiguous cases (json/geojson) since a .geojson source can
    turn out to have no real geometry (e.g. an OGC Features service that always
    emits GeoJSON), and vice versa."""

    def test_geojson_without_geom_column_reports_json(
        self, staging_metadata_deps: SimpleNamespace
    ) -> None:
        mock_link = MagicMock()
        mock_link.integrity_title = "Tarifs"
        mock_link.source_file_name = "data.geojson"
        mock_link.source_file_type = FileType.GEOJSON
        mock_link.source_import_type = ImportType.URL
        mock_link.source_url = None
        mock_link.integrity_transformation = None
        mock_link.final_table_name = None
        staging_metadata_deps.load.return_value = (mock_link, MagicMock())
        staging_metadata_deps.table.return_value.c = {}  # no 'geom' column

        result = _call_get_staging_metadata()

        assert result.file_type == FileType.JSON

    def test_geojson_with_geom_column_stays_geojson(
        self, staging_metadata_deps: SimpleNamespace
    ) -> None:
        mock_link = MagicMock()
        mock_link.integrity_title = "Parcelles"
        mock_link.source_file_name = "data.geojson"
        mock_link.source_file_type = FileType.GEOJSON
        mock_link.source_import_type = ImportType.URL
        mock_link.source_url = None
        mock_link.integrity_transformation = None
        mock_link.final_table_name = None
        staging_metadata_deps.load.return_value = (mock_link, MagicMock())
        staging_metadata_deps.table.return_value.c = {"geom": MagicMock()}

        result = _call_get_staging_metadata()

        assert result.file_type == FileType.GEOJSON

    def test_json_with_geom_column_reports_geojson(
        self, staging_metadata_deps: SimpleNamespace
    ) -> None:
        """Symmetric case: a .json source whose staging table does have a geom
        column (e.g. valid GeoJSON uploaded with a .json extension)."""
        mock_link = MagicMock()
        mock_link.integrity_title = "Points"
        mock_link.source_file_name = "data.json"
        mock_link.source_file_type = FileType.JSON
        mock_link.source_import_type = ImportType.URL
        mock_link.source_url = None
        mock_link.integrity_transformation = None
        mock_link.final_table_name = None
        staging_metadata_deps.load.return_value = (mock_link, MagicMock())
        staging_metadata_deps.table.return_value.c = {"geom": MagicMock()}

        result = _call_get_staging_metadata()

        assert result.file_type == FileType.GEOJSON

    def test_non_ambiguous_file_type_is_left_untouched(
        self, staging_metadata_deps: SimpleNamespace
    ) -> None:
        """CSV/GPKG/etc. never go through the json/geojson override, regardless of
        whether the staging table happens to have a geom column."""
        mock_link = MagicMock()
        mock_link.integrity_title = "Communes"
        mock_link.source_file_name = "data.csv"
        mock_link.source_file_type = FileType.CSV
        mock_link.source_import_type = ImportType.URL
        mock_link.source_url = None
        mock_link.integrity_transformation = None
        mock_link.final_table_name = None
        staging_metadata_deps.load.return_value = (mock_link, MagicMock())
        staging_metadata_deps.table.return_value.c = {}

        result = _call_get_staging_metadata()

        assert result.file_type == FileType.CSV


class TestEditStagingDatabase:
    """Test edit_staging (PUT) with ImportType.DATABASE."""

    @pytest.mark.asyncio
    @patch("src.api.routes.ingestion.staging._trigger_staging_task")
    @patch("src.api.routes.ingestion.staging._remove_staging_table")
    @patch("src.api.routes.ingestion.staging._generate_staging_table_name", return_value="stg_test")
    @patch("src.api.routes.ingestion.staging.table_exists", return_value=True)
    @patch("src.api.routes.ingestion.staging.schema_exists", return_value=True)
    @patch("src.api.routes.ingestion.staging.source_db_key", new="SOURCE_DB_1")
    @patch("src.api.routes.ingestion.staging.source_engine")
    async def test_edit_staging_with_database_type(
        self,
        mock_engine: MagicMock,
        mock_schema: MagicMock,
        mock_table: MagicMock,
        mock_gen_table: MagicMock,
        mock_remove: MagicMock,
        mock_trigger: MagicMock,
    ) -> None:
        """edit_staging updates IntegrityLink fields for a database source."""
        link_id = uuid4()
        mock_link = MagicMock()
        mock_link.id = link_id
        mock_link.staging_table_name = "stg_old"
        mock_link.integrity_owner = "testuser"
        mock_link.integrity_organization = "testorg"

        mock_session = MagicMock()
        mock_session.get.return_value = mock_link

        mock_trigger.return_value = MagicMock(
            integrity_link_id=str(link_id),
            dag_id="staging_dag",
            dag_run_id="run_1",
            status="queued",
        )

        await edit_staging(
            session=mock_session,
            integrity_link_id=str(link_id),
            type=ImportType.DATABASE,
            url=None,
            file=None,
            auth_enabled=False,
            username=None,
            password=None,
            ftp_host=None,
            ftp_port=None,
            ftp_path=None,
            db_schema="geo",
            db_table="rivers",
            sec_username="testuser",
            sec_org="testorg",
        )

        assert mock_link.source_import_type == ImportType.DATABASE
        assert mock_link.source_url == f"{DB_URI_PREFIX}SOURCE_DB_1/geo/rivers"
        assert mock_link.source_file_name is None
        assert mock_link.source_file_type is None
        assert mock_link.staging_table_name == "stg_test"
        mock_remove.assert_called_once_with("stg_old")
        mock_session.commit.assert_called_once()
        mock_trigger.assert_called_once()
