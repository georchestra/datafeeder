"""Tests for API (OGC service) source type in staging endpoints."""

from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pandas as pd
import pytest
from fastapi import HTTPException

from src.api.routes.ingestion.staging import (
    _process_import_source,  # pyright: ignore[reportPrivateUsage]
    _stringify_temporal_columns,  # pyright: ignore[reportPrivateUsage]
    dag_failure_callback,
    dag_success_callback,
    edit_staging,
    get_staging_metadata,
)
from src.models.data_import import ImportType


class TestProcessImportSourceApi:
    """Test _process_import_source for ImportType.API."""

    @pytest.mark.asyncio
    async def test_valid_wfs_source(self) -> None:
        result = await _process_import_source(
            type=ImportType.API,
            service_url="https://example.com/wfs",
            layer_name="ns:buildings",
            service_protocol="wfs",
        )
        assert result.source == "https://example.com/wfs"
        assert result.url == "https://example.com/wfs"
        assert result.source_file_name is None
        assert result.source_file_type is None
        assert result.auth_enabled is False
        assert result.source_layer == "ns:buildings"
        assert result.source_protocol == "wfs"

    @pytest.mark.asyncio
    async def test_valid_ogc_api_features_source(self) -> None:
        result = await _process_import_source(
            type=ImportType.API,
            service_url="https://example.com/ogcapi",
            layer_name="buildings",
            service_protocol="ogcFeatures",
        )
        assert result.source_layer == "buildings"
        assert result.source_protocol == "ogcFeatures"

    @pytest.mark.asyncio
    async def test_default_protocol_is_wfs_when_not_provided(self) -> None:
        result = await _process_import_source(
            type=ImportType.API,
            service_url="https://example.com/wfs",
            layer_name="ns:rivers",
            service_protocol=None,
        )
        assert result.source_protocol == "wfs"

    @pytest.mark.asyncio
    async def test_missing_service_url_returns_400(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.API,
                service_url=None,
                layer_name="ns:buildings",
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_layer_name_returns_400(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.API,
                service_url="https://example.com/wfs",
                layer_name=None,
            )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_whitespace_is_stripped(self) -> None:
        result = await _process_import_source(
            type=ImportType.API,
            service_url="  https://example.com/wfs  ",
            layer_name="  ns:buildings  ",
            service_protocol="  wfs  ",
        )
        assert result.source == "https://example.com/wfs"
        assert result.source_layer == "ns:buildings"
        assert result.source_protocol == "wfs"

    @pytest.mark.asyncio
    async def test_invalid_protocol_returns_400(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await _process_import_source(
                type=ImportType.API,
                service_url="https://example.com/wfs",
                layer_name="ns:buildings",
                service_protocol="http",
            )
        assert exc_info.value.status_code == 400


class TestDagSuccessCallbackApiSource:
    """Test that delete_temp_file is not called for API sources."""

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_delete_not_called_for_api_source(self, mock_delete: MagicMock) -> None:
        mock_integrity_link = MagicMock()
        mock_integrity_link.source_url = "https://example.com/wfs"
        mock_integrity_link.source_import_type = ImportType.API
        mock_integrity_link.created_at = datetime.now(timezone.utc)

        mock_session = MagicMock()
        mock_session.get.return_value = mock_integrity_link

        dag_success_callback(session=mock_session, integrity_link_id=str(uuid4()))

        mock_delete.assert_not_called()


class TestGetStagingMetadataTitleFallbackApi:
    """Test title fallback and layer_name field for API import type."""

    @patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging")
    @patch("src.api.routes.ingestion.staging.select")
    @patch("src.api.routes.ingestion.staging.Table")
    @patch("src.api.routes.ingestion.staging._resolve_columns")
    @patch("src.api.routes.ingestion.staging._detect_original_projection")
    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_title_falls_back_to_layer_name(
        self,
        mock_load: MagicMock,
        mock_detect_proj: MagicMock,
        mock_resolve_cols: MagicMock,
        mock_table: MagicMock,
        mock_select: MagicMock,
        mock_get_schema: MagicMock,
    ) -> None:
        """Title is source_layer when no integrity_title or source_file_name is set."""
        mock_link = MagicMock()
        mock_link.integrity_title = None
        mock_link.source_file_name = None
        mock_link.source_file_type = None
        mock_link.source_import_type = ImportType.API
        mock_link.source_url = "https://example.com/wfs"
        mock_link.source_layer = "ns:buildings"
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

        assert result.title == "ns:buildings"

    @patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging")
    @patch("src.api.routes.ingestion.staging.select")
    @patch("src.api.routes.ingestion.staging.Table")
    @patch("src.api.routes.ingestion.staging._resolve_columns")
    @patch("src.api.routes.ingestion.staging._detect_original_projection")
    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_layer_name_returned_in_response_for_api_type(
        self,
        mock_load: MagicMock,
        mock_detect_proj: MagicMock,
        mock_resolve_cols: MagicMock,
        mock_table: MagicMock,
        mock_select: MagicMock,
        mock_get_schema: MagicMock,
    ) -> None:
        """layer_name field in response matches source_layer for API import type."""
        mock_link = MagicMock()
        mock_link.integrity_title = "My WFS Layer"
        mock_link.source_file_name = None
        mock_link.source_file_type = None
        mock_link.source_import_type = ImportType.API
        mock_link.source_url = "https://example.com/wfs"
        mock_link.source_layer = "ns:buildings"
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

        assert result.title == "My WFS Layer"
        assert result.layer_name == "ns:buildings"

    @patch("src.api.routes.ingestion.staging.get_staging_schema", return_value="staging")
    @patch("src.api.routes.ingestion.staging.select")
    @patch("src.api.routes.ingestion.staging.Table")
    @patch("src.api.routes.ingestion.staging._resolve_columns")
    @patch("src.api.routes.ingestion.staging._detect_original_projection")
    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_layer_name_is_none_for_non_api_import_type(
        self,
        mock_load: MagicMock,
        mock_detect_proj: MagicMock,
        mock_resolve_cols: MagicMock,
        mock_table: MagicMock,
        mock_select: MagicMock,
        mock_get_schema: MagicMock,
    ) -> None:
        """layer_name is None in response for non-API import types."""
        mock_link = MagicMock()
        mock_link.integrity_title = "My File"
        mock_link.source_file_name = "data.gpkg"
        mock_link.source_file_type = "gpkg"
        mock_link.source_import_type = ImportType.FILE
        mock_link.source_url = "/tmp/data.gpkg"
        mock_link.source_layer = None
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

        assert result.layer_name is None


class TestEditStagingApi:
    """Test edit_staging (PUT) with ImportType.API."""

    @pytest.mark.asyncio
    @patch("src.api.routes.ingestion.staging._trigger_staging_task")
    @patch("src.api.routes.ingestion.staging._remove_staging_table")
    @patch("src.api.routes.ingestion.staging._generate_staging_table_name", return_value="stg_api")
    async def test_edit_staging_with_api_type_stores_layer_and_protocol(
        self,
        mock_gen_table: MagicMock,
        mock_remove: MagicMock,
        mock_trigger: MagicMock,
    ) -> None:
        """edit_staging sets source_layer and source_protocol on the integrity link."""
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
            type=ImportType.API,
            url=None,
            file=None,
            auth_enabled=False,
            username=None,
            password=None,
            ftp_host=None,
            ftp_port=None,
            ftp_path=None,
            db_schema=None,
            db_table=None,
            service_url="https://example.com/wfs",
            layer_name="ns:buildings",
            service_protocol="wfs",
            sec_username="testuser",
            sec_org="testorg",
        )

        assert mock_link.source_import_type == ImportType.API
        assert mock_link.source_url == "https://example.com/wfs"
        assert mock_link.source_layer == "ns:buildings"
        assert mock_link.source_protocol == "wfs"
        assert mock_link.source_file_type is None
        assert mock_link.staging_table_name == "stg_api"
        mock_remove.assert_called_once_with("stg_old")
        mock_session.commit.assert_called_once()
        mock_trigger.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.api.routes.ingestion.staging._trigger_staging_task")
    @patch("src.api.routes.ingestion.staging._remove_staging_table")
    @patch("src.api.routes.ingestion.staging._generate_staging_table_name", return_value="stg_api")
    async def test_trigger_staging_task_receives_layer_and_protocol(
        self,
        mock_gen_table: MagicMock,
        mock_remove: MagicMock,
        mock_trigger: MagicMock,
    ) -> None:
        """_trigger_staging_task is called with source_layer and source_protocol."""
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
            type=ImportType.API,
            url=None,
            file=None,
            auth_enabled=False,
            username=None,
            password=None,
            ftp_host=None,
            ftp_port=None,
            ftp_path=None,
            db_schema=None,
            db_table=None,
            service_url="https://example.com/ogcapi",
            layer_name="parcels",
            service_protocol="ogcFeatures",
            sec_username="testuser",
            sec_org="testorg",
        )

        call_kwargs = mock_trigger.call_args.kwargs
        assert call_kwargs["source_layer"] == "parcels"
        assert call_kwargs["source_protocol"] == "ogcFeatures"


class TestOapifUrlNormalization:
    """URL normalization for OGC API Features source URLs."""

    @pytest.mark.asyncio
    async def test_submit_staging_oapif_collections_url_normalized(self) -> None:
        """submit_staging strips /collections/... from the service URL before storing."""
        result = await _process_import_source(
            type=ImportType.API,
            service_url="https://example.com/v1/collections/my_layer",
            layer_name="my_layer",
            service_protocol="ogcFeatures",
        )
        assert result.url == "https://example.com/v1"
        assert result.source == "https://example.com/v1"

    @pytest.mark.asyncio
    async def test_submit_staging_oapif_items_url_normalized(self) -> None:
        """submit_staging strips /collections/.../items from the service URL before storing."""
        result = await _process_import_source(
            type=ImportType.API,
            service_url="https://example.com/v1/collections/my_layer/items",
            layer_name="my_layer",
            service_protocol="ogcFeatures",
        )
        assert result.url == "https://example.com/v1"
        assert result.source == "https://example.com/v1"

    @pytest.mark.asyncio
    async def test_submit_staging_oapif_bare_collections_url_normalized(self) -> None:
        """submit_staging strips bare /collections suffix from the service URL."""
        result = await _process_import_source(
            type=ImportType.API,
            service_url="https://example.com/v1/collections",
            layer_name="my_layer",
            service_protocol="ogcFeatures",
        )
        assert result.url == "https://example.com/v1"


class TestDagSuccessCallbackTempFile:
    """Test temp upload file cleanup in the staging success callback."""

    def _call(self, import_type: ImportType, source_url: str) -> None:
        link = MagicMock()
        link.source_url = source_url
        link.source_import_type = import_type
        link.created_at = datetime.now(timezone.utc)

        session = MagicMock()
        session.get.return_value = link

        dag_success_callback(session=session, integrity_link_id=str(uuid4()))

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_temp_file_deleted_for_file_import(self, mock_delete: MagicMock) -> None:
        url = "http://backend:8000/internal/files/data_abc.gpkg"

        self._call(ImportType.FILE, url)

        mock_delete.assert_called_once_with(url)

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_temp_file_not_deleted_for_url_import(self, mock_delete: MagicMock) -> None:
        self._call(ImportType.URL, "https://example.com/data.gpkg")

        mock_delete.assert_not_called()

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_temp_file_not_deleted_for_ftp_import(self, mock_delete: MagicMock) -> None:
        self._call(ImportType.FTP, "ftp://host:21/data.gpkg")

        mock_delete.assert_not_called()

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_temp_file_not_deleted_for_database_import(self, mock_delete: MagicMock) -> None:
        self._call(ImportType.DATABASE, "db://main/public/my_table")

        mock_delete.assert_not_called()

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_delete_error_is_swallowed(self, mock_delete: MagicMock) -> None:
        mock_delete.side_effect = IOError("already gone")

        self._call(ImportType.FILE, "http://backend:8000/internal/files/data_abc.gpkg")  # no raise


class TestDagFailureCallbackTempFile:
    """Test temp upload file cleanup in the staging failure callback."""

    def _make_link(
        self,
        import_type: ImportType,
        last_retrieval: datetime | None = None,
    ) -> MagicMock:
        link = MagicMock()
        link.source_url = "http://backend:8000/internal/files/data_abc.gpkg"
        link.source_import_type = import_type
        link.staging_table_name = "staging_abc"
        link.last_retrieval_timestamp = last_retrieval
        return link

    def _call(self, link: MagicMock) -> tuple[MagicMock, MagicMock]:
        datafeeder_session = MagicMock()
        datafeeder_session.get.return_value = link
        data_session = MagicMock()

        with (
            patch("src.api.routes.ingestion.staging.Table"),
            patch("src.api.routes.ingestion.staging.data_engine"),
        ):
            dag_failure_callback(
                datafeeder_session=datafeeder_session,
                data_session=data_session,
                integrity_link_id=str(uuid4()),
                dag_id="staging_dag",
                dag_run_id="run-1",
                reason=None,
            )
        return datafeeder_session, data_session

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_temp_file_deleted_for_file_import(self, mock_delete: MagicMock) -> None:
        link = self._make_link(ImportType.FILE)

        datafeeder_session, _ = self._call(link)

        mock_delete.assert_called_once_with(link.source_url)
        datafeeder_session.delete.assert_called_once_with(link)

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_temp_file_not_deleted_for_database_import(self, mock_delete: MagicMock) -> None:
        link = self._make_link(ImportType.DATABASE)

        self._call(link)

        mock_delete.assert_not_called()

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_temp_file_not_deleted_for_api_import(self, mock_delete: MagicMock) -> None:
        link = self._make_link(ImportType.API)

        self._call(link)

        mock_delete.assert_not_called()

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_temp_file_deleted_on_rerun_but_link_kept(self, mock_delete: MagicMock) -> None:
        link = self._make_link(ImportType.FILE, last_retrieval=datetime.now(timezone.utc))

        datafeeder_session, _ = self._call(link)

        mock_delete.assert_called_once_with(link.source_url)
        datafeeder_session.delete.assert_not_called()

    @patch("src.api.routes.ingestion.staging.delete_temp_file")
    def test_delete_error_does_not_abort_cleanup(self, mock_delete: MagicMock) -> None:
        mock_delete.side_effect = IOError("already gone")
        link = self._make_link(ImportType.FILE)

        datafeeder_session, _ = self._call(link)

        datafeeder_session.delete.assert_called_once_with(link)


class TestStringifyTemporalColumns:
    """Preview data must be JSON-serializable; temporal columns get stringified."""

    def test_object_date_column_becomes_iso_strings(self) -> None:
        df = pd.DataFrame({"d": [date(2024, 1, 2), date(2024, 3, 4)]})
        assert df["d"].dtype == "object"

        _stringify_temporal_columns(df)

        assert df["d"].tolist() == ["2024-01-02", "2024-03-04"]

    def test_object_datetime_column_becomes_iso_strings(self) -> None:
        df = pd.DataFrame({"dt": [datetime(2024, 1, 2, 8, 30), datetime(2024, 3, 4, 9, 0)]})
        df["dt"] = df["dt"].astype(object)

        _stringify_temporal_columns(df)

        assert df["dt"].tolist() == ["2024-01-02T08:30:00", "2024-03-04T09:00:00"]

    def test_datetime64_column_becomes_strings(self) -> None:
        df = pd.DataFrame({"ts": pd.to_datetime(["2024-01-02", "2024-03-04"])})
        assert pd.api.types.is_datetime64_any_dtype(df["ts"])

        _stringify_temporal_columns(df)

        assert all(isinstance(v, str) for v in df["ts"])

    def test_non_temporal_columns_are_left_intact(self) -> None:
        df = pd.DataFrame({"name": ["a", "b"], "n": [1, 2]})

        _stringify_temporal_columns(df)

        assert df["name"].tolist() == ["a", "b"]
        assert df["n"].tolist() == [1, 2]

    def test_nulls_do_not_raise_and_are_preserved(self) -> None:
        df = pd.DataFrame({"d": [None, date(2024, 1, 2)]})

        _stringify_temporal_columns(df)

        assert df["d"].tolist() == [None, "2024-01-02"]
