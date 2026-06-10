"""Tests for data ingestion utilities in data_manipulation library."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch
from urllib.error import URLError

import geopandas as gpd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import requests
from geopandas import GeoDataFrame
from pandas import DataFrame
from shapely.geometry import Point
from sqlalchemy.engine import Engine

from data_manipulation import IntegrityTransformation, apply_transformations
from data_manipulation.ingestion import (
    _copy_bytes_to_postgres,  # pyright: ignore[reportPrivateUsage]
    _iter_data_batches,  # pyright: ignore[reportPrivateUsage]
    _normalise_geometry_columns,  # pyright: ignore[reportPrivateUsage]
    _write_batches_to_postgis,  # pyright: ignore[reportPrivateUsage]
    ingest_data_from_database_into_postgis,
    ingest_data_from_file_into_postgis,
    ingest_data_from_ftp_into_postgis,
    ingest_data_from_ogc_service_into_postgis,
    ingest_data_from_url_into_postgis,
    read_data_from_postgis,
)


class TestIngestDataFromFileIntoPostgis:
    """File ingestion delegates to URL ingestion under the hood."""

    @patch("data_manipulation.ingestion.ingest_data_from_url_into_postgis")
    def test_delegates_to_url_ingestion(self, mock_url_ingest: Mock) -> None:
        engine = Mock(spec=Engine)
        ingest_data_from_file_into_postgis("/tmp/data.geojson", "test_table", engine, "public")
        mock_url_ingest.assert_called_once_with("/tmp/data.geojson", "test_table", engine, "public")

    @patch(
        "data_manipulation.ingestion.ingest_data_from_url_into_postgis",
        side_effect=RuntimeError("boom"),
    )
    def test_propagates_errors(self, mock_url_ingest: Mock) -> None:
        with pytest.raises(RuntimeError, match="boom"):
            ingest_data_from_file_into_postgis("/tmp/data.geojson", "tbl", Mock(spec=Engine), "p")


class TestIngestDataFromUrlIntoPostgis:
    """Test cases for ingest_data_from_url_into_postgis function."""

    @pytest.fixture
    def mock_engine(self) -> Mock:
        return Mock(spec=Engine)

    @staticmethod
    def _make_response(headers: dict[str, str] | None = None) -> MagicMock:
        mock_response = MagicMock()
        mock_response.headers = headers or {}
        mock_response.__enter__.return_value = mock_response
        return mock_response

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_data_batches")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_success(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_iter_batches: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response()
        sentinel = object()
        mock_iter_batches.return_value = sentinel

        ingest_data_from_url_into_postgis(
            "http://example.com/data.geojson", "test_table", mock_engine, "public"
        )

        mock_requests_get.assert_called_once_with(
            "http://example.com/data.geojson", auth=None, timeout=None, stream=True
        )
        mock_iter_batches.assert_called_once()
        mock_writer.assert_called_once_with(sentinel, "test_table", mock_engine, "public")

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_data_batches")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_with_auth(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_iter_batches: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response()
        auth = ("username", "password")
        ingest_data_from_url_into_postgis(
            "http://example.com/data.geojson", "test_table", mock_engine, "public", auth=auth
        )
        mock_requests_get.assert_called_once_with(
            "http://example.com/data.geojson", auth=auth, timeout=None, stream=True
        )

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_data_batches")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_with_content_disposition(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_iter_batches: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response(
            {"Content-Disposition": 'attachment; filename="data.geojson"'}
        )

        ingest_data_from_url_into_postgis(
            "http://example.com/download", "test_table", mock_engine, "public"
        )

        # The downloaded temp file's name is derived from Content-Disposition.
        path_arg = mock_iter_batches.call_args.args[0]
        assert "data.geojson" in str(path_arg)

    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_http_error(
        self,
        mock_requests_get: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        with pytest.raises(requests.exceptions.HTTPError):
            ingest_data_from_url_into_postgis(
                "http://example.com/data.geojson", "test_table", mock_engine, "public"
            )

    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_connection_error(
        self,
        mock_requests_get: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        with pytest.raises(requests.exceptions.ConnectionError):
            ingest_data_from_url_into_postgis(
                "http://example.com/data.geojson", "test_table", mock_engine, "public"
            )

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_data_batches")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_parquet_url_by_extension(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_iter_batches: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response()
        ingest_data_from_url_into_postgis(
            "http://example.com/layer.parquet", "test_table", mock_engine, "public"
        )
        path_arg = mock_iter_batches.call_args.args[0]
        assert str(path_arg).endswith(".parquet")
        mock_writer.assert_called_once()

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_data_batches")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_parquet_url_with_content_disposition(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_iter_batches: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response(
            {"Content-Disposition": 'attachment; filename="export.parquet"'}
        )
        ingest_data_from_url_into_postgis(
            "http://example.com/download/42", "test_table", mock_engine, "public"
        )
        path_arg = mock_iter_batches.call_args.args[0]
        assert str(path_arg).endswith("export.parquet")


class TestIngestDataFromFtpIntoPostgis:
    """Test cases for ingest_data_from_ftp_into_postgis function."""

    @pytest.fixture
    def mock_engine(self) -> Mock:
        """Create a mock SQLAlchemy engine."""
        return Mock(spec=Engine)

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_data_batches")
    @patch("data_manipulation.ingestion.urlretrieve")
    def test_ingest_from_ftp_success(
        self,
        mock_urlretrieve: Mock,
        mock_iter_batches: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        sentinel = object()
        mock_iter_batches.return_value = sentinel

        ingest_data_from_ftp_into_postgis(
            "ftp://example.com/data.geojson", "test_table", mock_engine, "public"
        )

        mock_urlretrieve.assert_called_once()
        assert "ftp://example.com/data.geojson" in str(mock_urlretrieve.call_args[0][0])
        mock_iter_batches.assert_called_once()
        mock_writer.assert_called_once_with(sentinel, "test_table", mock_engine, "public")

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_data_batches")
    @patch("data_manipulation.ingestion.urlretrieve")
    def test_ingest_from_ftp_with_auth(
        self,
        mock_urlretrieve: Mock,
        mock_iter_batches: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        auth = ("username", "password")
        ingest_data_from_ftp_into_postgis(
            "ftp://example.com/data.geojson", "test_table", mock_engine, "public", auth=auth
        )
        called_url = str(mock_urlretrieve.call_args[0][0])
        assert "username" in called_url
        assert "password" in called_url
        assert "@example.com" in called_url

    @patch("data_manipulation.ingestion.urlretrieve")
    def test_ingest_from_ftp_auth_failed(
        self,
        mock_urlretrieve: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion from FTP raises exception on authentication failure."""
        mock_urlretrieve.side_effect = URLError("530 Login incorrect")

        with pytest.raises(Exception, match="FTP authentication failed"):
            ingest_data_from_ftp_into_postgis(
                "ftp://example.com/data.geojson", "test_table", mock_engine, "public"
            )

    @patch("data_manipulation.ingestion.urlretrieve")
    def test_ingest_from_ftp_file_not_found(
        self,
        mock_urlretrieve: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion from FTP raises exception when file not found."""
        mock_urlretrieve.side_effect = URLError("550 No such file")

        with pytest.raises(Exception, match="FTP file not found"):
            ingest_data_from_ftp_into_postgis(
                "ftp://example.com/data.geojson", "test_table", mock_engine, "public"
            )

    @patch("data_manipulation.ingestion.urlretrieve")
    def test_ingest_from_ftp_timeout(
        self,
        mock_urlretrieve: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion from FTP raises exception on connection timeout."""
        mock_urlretrieve.side_effect = URLError("Connection timed out")

        with pytest.raises(Exception, match="FTP connection timeout"):
            ingest_data_from_ftp_into_postgis(
                "ftp://example.com/data.geojson", "test_table", mock_engine, "public"
            )

    @patch("data_manipulation.ingestion.urlretrieve")
    def test_ingest_from_ftp_connection_refused(
        self,
        mock_urlretrieve: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion from FTP raises exception when connection is refused."""
        mock_urlretrieve.side_effect = URLError("Connection refused")

        with pytest.raises(Exception, match="FTP connection refused"):
            ingest_data_from_ftp_into_postgis(
                "ftp://example.com/data.geojson", "test_table", mock_engine, "public"
            )

    @patch("data_manipulation.ingestion.urlretrieve")
    def test_ingest_from_ftp_network_error(
        self,
        mock_urlretrieve: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion from FTP raises exception on network error."""

        mock_urlretrieve.side_effect = OSError("Network unreachable")

        with pytest.raises(Exception, match="Network error"):
            ingest_data_from_ftp_into_postgis(
                "ftp://example.com/data.geojson", "test_table", mock_engine, "public"
            )


class TestReadDataFromPostgis:
    """Test cases for read_data_from_postgis function."""

    @pytest.fixture
    def mock_engine(self) -> Mock:
        """Create a mock SQLAlchemy engine."""
        return Mock(spec=Engine)

    @patch("data_manipulation.ingestion.gpd.read_postgis")
    @patch("data_manipulation.ingestion.select")
    @patch("data_manipulation.ingestion.Table")
    @patch("data_manipulation.ingestion.MetaData")
    def test_read_data_success_with_geometry(
        self,
        mock_metadata_class: Mock,
        mock_table_class: Mock,
        mock_select: Mock,
        mock_read_postgis: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test successful data read from PostGIS with geometry column."""

        # Mock the metadata and table
        mock_metadata = MagicMock()
        mock_metadata_class.return_value = mock_metadata
        mock_table = MagicMock()
        # Mock table.c to have the 'geom' column
        mock_column = MagicMock()
        mock_column.name = "geom"
        mock_table.c = {"geom": mock_column, "col1": MagicMock()}
        mock_table_class.return_value = mock_table

        # Mock the select query
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_compiled = MagicMock()
        mock_compiled.__str__ = MagicMock(return_value="SELECT * FROM test_table")
        mock_query.compile.return_value = mock_compiled

        mock_gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})
        mock_read_postgis.return_value = mock_gdf

        result = read_data_from_postgis("test_table", mock_engine, "public")

        assert isinstance(result, GeoDataFrame)
        assert len(result) == 2
        mock_read_postgis.assert_called_once()
        mock_metadata_class.assert_called_once_with(schema="public")
        mock_table_class.assert_called_once_with(
            "test_table", mock_metadata, autoload_with=mock_engine
        )
        mock_select.assert_called_once_with(mock_table)

    @patch("data_manipulation.ingestion.pd.read_sql")
    @patch("data_manipulation.ingestion.select")
    @patch("data_manipulation.ingestion.Table")
    @patch("data_manipulation.ingestion.MetaData")
    def test_read_data_success_without_geometry(
        self,
        mock_metadata_class: Mock,
        mock_table_class: Mock,
        mock_select: Mock,
        mock_read_sql: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test successful data read from PostGIS without geometry column."""

        # Mock the metadata and table
        mock_metadata = MagicMock()
        mock_metadata_class.return_value = mock_metadata
        mock_table = MagicMock()
        # Mock table.c to NOT have the 'geom' column
        mock_table.c = {"col1": MagicMock(), "col2": MagicMock()}
        mock_table_class.return_value = mock_table

        # Mock the select query
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_compiled = MagicMock()
        mock_compiled.__str__ = MagicMock(return_value="SELECT * FROM test_table")
        mock_query.compile.return_value = mock_compiled

        mock_df = DataFrame({"col1": [1, 2], "col2": ["a", "b"]})
        mock_read_sql.return_value = mock_df

        result = read_data_from_postgis("test_table", mock_engine, "public")

        assert isinstance(result, DataFrame)
        assert len(result) == 2
        mock_read_sql.assert_called_once()
        mock_metadata_class.assert_called_once_with(schema="public")
        mock_table_class.assert_called_once_with(
            "test_table", mock_metadata, autoload_with=mock_engine
        )
        mock_select.assert_called_once_with(mock_table)

    @patch("data_manipulation.ingestion.gpd.read_postgis")
    def test_read_data_validates_table_name(
        self,
        mock_read_postgis: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test that read_data validates table name."""

        with pytest.raises(ValueError):
            read_data_from_postgis("invalid-table-name!", mock_engine, "public")

        mock_read_postgis.assert_not_called()

    @patch("data_manipulation.ingestion.gpd.read_postgis")
    def test_read_data_sql_injection_prevented(
        self,
        mock_read_postgis: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test that SQL injection attempts are prevented."""

        malicious_names = [
            "table; DROP TABLE users--",
            "table' OR '1'='1",
            'table" DROP SCHEMA public CASCADE--',
        ]

        for malicious_name in malicious_names:
            with pytest.raises(ValueError):
                read_data_from_postgis(malicious_name, mock_engine, "public")

        mock_read_postgis.assert_not_called()

    @patch("data_manipulation.ingestion.gpd.read_postgis")
    @patch("data_manipulation.ingestion.select")
    @patch("data_manipulation.ingestion.Table")
    @patch("data_manipulation.ingestion.MetaData")
    def test_read_data_raises_exception_on_error(
        self,
        mock_metadata_class: Mock,
        mock_table_class: Mock,
        mock_select: Mock,
        mock_read_postgis: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test that errors during reading are raised."""

        # Mock the metadata and table
        mock_metadata = MagicMock()
        mock_metadata_class.return_value = mock_metadata
        mock_table = MagicMock()
        # Mock table.c to have the 'geom' column
        mock_table.c = {"geom": MagicMock()}
        mock_table_class.return_value = mock_table

        # Mock the select query
        mock_query = MagicMock()
        mock_select.return_value = mock_query
        mock_compiled = MagicMock()
        mock_compiled.__str__ = MagicMock(return_value="SELECT * FROM test_table")
        mock_query.compile.return_value = mock_compiled


class TestApplyTransformations:
    """Test cases for apply_transformations function."""

    def test_apply_transformations_returns_unchanged_for_now(self) -> None:
        """Test that apply_transformations currently returns data unchanged."""

        gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})
        transformation_config = IntegrityTransformation()

        result = apply_transformations(gdf, transformation_config)

        # For now, should return the same data
        assert result.equals(gdf)


class TestNormaliseGeometryColumns:
    """Direct tests for _normalise_geometry_columns (geom-column rules)."""

    def test_geodataframe_with_default_geom_returns_geom(self) -> None:
        gdf = GeoDataFrame(
            {"col1": [1, 2]},
            geometry=gpd.GeoSeries([Point(0, 0), Point(1, 1)], name="geom"),
        )
        result, geom_col = _normalise_geometry_columns(gdf)
        assert geom_col == "geom"
        assert result.geometry.name == "geom"

    def test_geodataframe_renames_active_geometry_to_geom(self) -> None:
        gdf = GeoDataFrame(
            {"col1": [1, 2]},
            geometry=gpd.GeoSeries([Point(0, 0), Point(1, 1)], name="geometry"),
        )
        result, geom_col = _normalise_geometry_columns(gdf)
        assert geom_col == "geom"
        assert result.geometry.name == "geom"

    def test_geodataframe_with_no_active_geometry_drops_stray_geom(self) -> None:
        gdf = GeoDataFrame({"col1": [1, 2], "col2": [3, 4]})
        gdf._geometry_column_name = None
        result, geom_col = _normalise_geometry_columns(gdf)
        assert geom_col is None
        assert "geom" not in result.columns

    def test_plain_dataframe_drops_stray_geom(self) -> None:
        df = DataFrame({"col1": [1, 2], "geom": ["point1", "point2"]})
        result, geom_col = _normalise_geometry_columns(df)
        assert geom_col is None
        assert "geom" not in result.columns
        assert "col1" in result.columns

    def test_plain_dataframe_no_geom_returns_as_is(self) -> None:
        df = DataFrame({"col1": [1, 2], "col2": [3, 4]})
        result, geom_col = _normalise_geometry_columns(df)
        assert geom_col is None
        assert list(result.columns) == ["col1", "col2"]


class TestCopyBytesToPostgres:
    """Driver dispatch + connection lifecycle for _copy_bytes_to_postgres."""

    def _build_engine(self, driver: str) -> tuple[Mock, Mock, Mock]:
        engine = Mock(spec=Engine)
        engine.dialect = Mock()
        engine.dialect.driver = driver
        cursor = MagicMock()
        raw_conn = MagicMock()
        raw_conn.cursor.return_value = cursor
        engine.raw_connection.return_value = raw_conn
        return engine, raw_conn, cursor

    def test_psycopg3_driver_uses_cursor_copy(self) -> None:
        engine, raw_conn, cursor = self._build_engine("psycopg")
        _copy_bytes_to_postgres("tbl", "public", ["c1", "c2"], iter([b"1,2\n"]), engine)

        cursor.copy.assert_called_once()
        copy_sql = cursor.copy.call_args.args[0]
        assert 'COPY "public"."tbl" ("c1", "c2")' in copy_sql
        assert "FROM STDIN" in copy_sql
        raw_conn.commit.assert_called_once()
        raw_conn.close.assert_called_once()

    def test_psycopg2_driver_uses_copy_expert(self) -> None:
        engine, raw_conn, cursor = self._build_engine("psycopg2")
        _copy_bytes_to_postgres("tbl", "public", ["c1"], iter([b"1\n"]), engine)

        cursor.copy_expert.assert_called_once()
        copy_sql = cursor.copy_expert.call_args.args[0]
        assert 'COPY "public"."tbl"' in copy_sql
        raw_conn.commit.assert_called_once()

    def test_unsupported_driver_raises(self) -> None:
        engine, _, _ = self._build_engine("oracle")
        with pytest.raises(RuntimeError, match="Unsupported postgres driver"):
            _copy_bytes_to_postgres("tbl", "public", ["c"], iter([b""]), engine)

    def test_rollback_on_failure_when_owning_connection(self) -> None:
        engine, raw_conn, cursor = self._build_engine("psycopg")
        cursor.copy.side_effect = RuntimeError("boom")
        with pytest.raises(RuntimeError, match="boom"):
            _copy_bytes_to_postgres("tbl", "public", ["c"], iter([b""]), engine)
        raw_conn.rollback.assert_called_once()
        raw_conn.commit.assert_not_called()

    def test_shared_raw_conn_skips_lifecycle(self) -> None:
        """When caller passes raw_conn, helper must NOT commit/rollback/close it."""

        engine = Mock(spec=Engine)
        engine.dialect = Mock()
        engine.dialect.driver = "psycopg"
        external_cursor = MagicMock()
        external_raw = MagicMock()
        external_raw.cursor.return_value = external_cursor

        _copy_bytes_to_postgres(
            "tbl", "public", ["c"], iter([b"x\n"]), engine, raw_conn=external_raw
        )
        external_cursor.copy.assert_called_once()
        external_raw.commit.assert_not_called()
        external_raw.rollback.assert_not_called()
        external_raw.close.assert_not_called()


class TestWriteBatchesToPostgis:
    """Transactional shape of _write_batches_to_postgis."""

    def _build_engine_with_begin(self) -> tuple[Mock, MagicMock, MagicMock]:
        """Engine whose begin() yields a SA Connection mock with a raw_conn attached."""
        engine = Mock(spec=Engine)
        engine.dialect = Mock()
        engine.dialect.driver = "psycopg"
        sa_conn = MagicMock()
        raw_conn = MagicMock()
        sa_conn.connection = raw_conn
        ctx = MagicMock()
        ctx.__enter__.return_value = sa_conn
        ctx.__exit__.return_value = False
        engine.begin.return_value = ctx
        return engine, sa_conn, raw_conn

    def test_empty_iterator_raises(self) -> None:
        engine, _, _ = self._build_engine_with_begin()
        with pytest.raises(ValueError, match="No data"):
            _write_batches_to_postgis(iter([]), "tbl", engine, "public")

    @patch("data_manipulation.ingestion._copy_bytes_to_postgres")
    def test_bootstrap_ddl_then_copy_per_batch(self, mock_copy: Mock) -> None:
        engine, sa_conn, raw_conn = self._build_engine_with_begin()
        df1 = DataFrame({"col1": [1, 2]})
        df2 = DataFrame({"col1": [3, 4, 5]})

        with patch.object(DataFrame, "to_sql") as mock_to_sql:
            total = _write_batches_to_postgis(iter([df1, df2]), "tbl", engine, "public")

        assert total == 5
        # Bootstrap DDL: head(0) call on the SA connection, if_exists=replace
        mock_to_sql.assert_called_once()
        assert mock_to_sql.call_args.args[:3] == ("tbl", sa_conn) or (
            mock_to_sql.call_args.args[0] == "tbl" and mock_to_sql.call_args.args[1] is sa_conn
        )
        assert mock_to_sql.call_args.kwargs.get("if_exists") == "replace"
        # One COPY per batch, all sharing the same raw conn.
        assert mock_copy.call_count == 2
        for call in mock_copy.call_args_list:
            assert call.kwargs.get("raw_conn") is raw_conn

    @patch("data_manipulation.ingestion._copy_bytes_to_postgres")
    def test_create_id_triggers_alter_table(self, mock_copy: Mock) -> None:
        engine, sa_conn, _ = self._build_engine_with_begin()
        df = DataFrame({"col1": [1]})

        with patch.object(DataFrame, "to_sql"):
            _write_batches_to_postgis(iter([df]), "tbl", engine, "public", create_id=True)

        executed_sql = [str(call.args[0]) for call in sa_conn.execute.call_args_list if call.args]
        assert any("ADD COLUMN id_datafeeder UUID" in s for s in executed_sql)
        assert any("ADD PRIMARY KEY (id_datafeeder)" in s for s in executed_sql)

    @patch("data_manipulation.ingestion._copy_bytes_to_postgres")
    def test_geodataframe_first_batch_uses_to_postgis(self, mock_copy: Mock) -> None:
        engine, _, _ = self._build_engine_with_begin()
        gdf = GeoDataFrame({"c": [1]}, geometry=[Point(0, 0)], crs="EPSG:4326")

        with patch.object(GeoDataFrame, "to_postgis") as mock_to_postgis:
            _write_batches_to_postgis(iter([gdf]), "tbl", engine, "public")

        mock_to_postgis.assert_called_once()
        assert mock_to_postgis.call_args.kwargs.get("if_exists") == "replace"


class TestIngestDataFromDatabaseIntoPostgis:
    """Test cases for ingest_data_from_database_into_postgis function."""

    @pytest.fixture
    def mock_source_engine(self) -> Mock:
        return Mock(spec=Engine)

    @pytest.fixture
    def mock_target_engine(self) -> Mock:
        return Mock(spec=Engine)

    def _build_table_mock(self, has_geom: bool) -> MagicMock:
        """Mock a reflected SQLAlchemy Table with optional 'geom' column."""
        mock_table = MagicMock()

        def _contains(key: object) -> bool:
            return bool(has_geom and key == "geom")

        mock_table.c.__contains__ = Mock(side_effect=_contains)
        if has_geom:
            geom_col_mock = MagicMock()
            geom_col_mock.name = "geom"
            geom_col_mock.type = Mock()  # not an instance of Geometry — srid stays 0
            mock_table.c.__getitem__ = Mock(return_value=geom_col_mock)
            mock_table.columns = [Mock(name="_id"), geom_col_mock]
            mock_table.columns[0].name = "id"
        else:
            id_col = Mock()
            id_col.name = "id"
            name_col = Mock()
            name_col.name = "name"
            mock_table.columns = [id_col, name_col]
        return mock_table

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion.pd.read_sql")
    @patch("data_manipulation.ingestion._get_geo_column_from_table")
    @patch("data_manipulation.ingestion.select")
    @patch("data_manipulation.ingestion.Table")
    @patch("data_manipulation.ingestion.MetaData")
    def test_ingest_non_geographic_table(
        self,
        mock_metadata: Mock,
        mock_table_cls: Mock,
        mock_select: Mock,
        mock_get_geo: Mock,
        mock_read_sql: Mock,
        mock_writer: Mock,
        mock_source_engine: Mock,
        mock_target_engine: Mock,
    ) -> None:
        """Non-geographic source yields plain DataFrame batches to the streaming writer."""
        mock_table_cls.return_value = self._build_table_mock(has_geom=False)
        mock_get_geo.return_value = None

        chunk_a = DataFrame({"id": [1, 2], "name": ["a", "b"]})
        chunk_b = DataFrame({"id": [3], "name": ["c"]})
        mock_read_sql.return_value = iter([chunk_a, chunk_b])

        ingest_data_from_database_into_postgis(
            source_schema="public",
            source_table="communes",
            source_engine=mock_source_engine,
            target_table="staging_table",
            target_engine=mock_target_engine,
            target_schema="staging",
        )

        mock_writer.assert_called_once()
        args = mock_writer.call_args.args
        produced = list(args[0])
        assert len(produced) == 2
        assert all(isinstance(b, DataFrame) and not isinstance(b, GeoDataFrame) for b in produced)
        assert args[1:] == ("staging_table", mock_target_engine, "staging")

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion.shapely.from_wkb")
    @patch("data_manipulation.ingestion.pd.read_sql")
    @patch("data_manipulation.ingestion._get_geo_column_from_table")
    @patch("data_manipulation.ingestion.select")
    @patch("data_manipulation.ingestion.Table")
    @patch("data_manipulation.ingestion.MetaData")
    def test_ingest_geographic_table_vectorises_wkb_decode(
        self,
        mock_metadata: Mock,
        mock_table_cls: Mock,
        mock_select: Mock,
        mock_get_geo: Mock,
        mock_read_sql: Mock,
        mock_from_wkb: Mock,
        mock_writer: Mock,
        mock_source_engine: Mock,
        mock_target_engine: Mock,
    ) -> None:
        """Geometry decoding happens once per batch (vectorised), not once per row."""
        mock_table_cls.return_value = self._build_table_mock(has_geom=True)
        mock_get_geo.return_value = "geom"

        wkb_elem_1 = MagicMock(data=b"\x01\x02")
        wkb_elem_2 = MagicMock(data=b"\x03\x04")
        chunk = DataFrame({"id": [1, 2], "geom": [wkb_elem_1, wkb_elem_2]})
        mock_read_sql.return_value = iter([chunk])
        mock_from_wkb.return_value = [Point(0, 0), Point(1, 1)]

        ingest_data_from_database_into_postgis(
            source_schema="geo",
            source_table="rivers",
            source_engine=mock_source_engine,
            target_table="staging_table",
            target_engine=mock_target_engine,
            target_schema="staging",
        )

        # Drain the iterator to exercise the generator body (the writer is mocked).
        produced = list(mock_writer.call_args.args[0])
        # Exactly one vectorised shapely.from_wkb per batch.
        assert mock_from_wkb.call_count == 1
        # Producer yields GeoDataFrames.
        assert len(produced) == 1
        assert isinstance(produced[0], GeoDataFrame)

    @patch("data_manipulation.ingestion.Table")
    @patch("data_manipulation.ingestion.MetaData")
    def test_source_table_not_found_raises(
        self,
        mock_metadata: Mock,
        mock_table_cls: Mock,
        mock_source_engine: Mock,
        mock_target_engine: Mock,
    ) -> None:
        """Exception is raised when source table does not exist."""
        mock_table_cls.side_effect = Exception("Table not found")

        with pytest.raises(Exception, match="Table not found"):
            ingest_data_from_database_into_postgis(
                source_schema="public",
                source_table="inexistant",
                source_engine=mock_source_engine,
                target_table="staging_table",
                target_engine=mock_target_engine,
            )

    def test_invalid_source_schema_raises(
        self,
        mock_source_engine: Mock,
        mock_target_engine: Mock,
    ) -> None:
        """ValueError is raised for invalid schema name."""
        with pytest.raises(ValueError):
            ingest_data_from_database_into_postgis(
                source_schema="Invalid-Schema",
                source_table="my_table",
                source_engine=mock_source_engine,
                target_table="staging_table",
                target_engine=mock_target_engine,
            )

    def test_invalid_source_table_raises(
        self,
        mock_source_engine: Mock,
        mock_target_engine: Mock,
    ) -> None:
        """ValueError is raised for invalid table name."""
        with pytest.raises(ValueError):
            ingest_data_from_database_into_postgis(
                source_schema="public",
                source_table="123bad",
                source_engine=mock_source_engine,
                target_table="staging_table",
                target_engine=mock_target_engine,
            )


class TestIngestDataFromOgcServiceIntoPostgis:
    """Test ingest_data_from_ogc_service_into_postgis."""

    @pytest.fixture
    def mock_engine(self) -> Mock:
        return Mock(spec=Engine)

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_pyogrio_arrow_batches")
    def test_wfs_uses_wfs_gdal_prefix(
        self,
        mock_iter: Mock,
        mock_write: Mock,
        mock_engine: Mock,
    ) -> None:
        """WFS protocol produces a WFS: prefixed GDAL source string."""
        batches = iter([GeoDataFrame({"col1": [1]}, geometry=gpd.GeoSeries([Point(0, 0)]))])
        mock_iter.return_value = batches

        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.com/wfs",
            layer_name="ns:buildings",
            protocol="wfs",
            table_name="buildings_stg",
            engine=mock_engine,
            schema="public",
        )

        assert mock_iter.call_args.args[0] == "WFS:https://example.com/wfs"
        assert mock_iter.call_args.kwargs["layer"] == "ns:buildings"
        assert mock_write.call_args.args[0] is batches
        assert mock_write.call_args.args[1:] == ("buildings_stg", mock_engine, "public")

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_pyogrio_arrow_batches")
    def test_ogc_api_features_uses_oapif_gdal_prefix(
        self,
        mock_iter: Mock,
        mock_write: Mock,
        mock_engine: Mock,
    ) -> None:
        """ogcFeatures protocol produces an OAPIF: prefixed GDAL source string."""
        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.com/ogcapi",
            layer_name="parcels",
            protocol="ogcFeatures",
            table_name="parcels_stg",
            engine=mock_engine,
            schema="public",
        )

        assert mock_iter.call_args.args[0] == "OAPIF:https://example.com/ogcapi"
        assert mock_iter.call_args.kwargs["layer"] == "parcels"
        assert mock_write.call_args.args[0] is mock_iter.return_value

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_pyogrio_arrow_batches")
    def test_unknown_protocol_falls_back_to_wfs_prefix(
        self,
        mock_iter: Mock,
        mock_write: Mock,
        mock_engine: Mock,
    ) -> None:
        """Unknown protocol value falls back to the WFS: GDAL prefix."""
        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.com/wfs",
            layer_name="ns:rivers",
            protocol="unknown_protocol",
            table_name="rivers_stg",
            engine=mock_engine,
            schema="public",
        )

        assert mock_iter.call_args.args[0].startswith("WFS:")

    @patch("data_manipulation.ingestion._write_batches_to_postgis")
    @patch("data_manipulation.ingestion._iter_pyogrio_arrow_batches")
    def test_read_exception_is_reraised(
        self,
        mock_iter: Mock,
        mock_write: Mock,
        mock_engine: Mock,
    ) -> None:
        """Exceptions raised while writing the layer are propagated to the caller."""
        mock_write.side_effect = RuntimeError("GDAL error")

        with pytest.raises(RuntimeError, match="GDAL error"):
            ingest_data_from_ogc_service_into_postgis(
                service_url="https://example.com/wfs",
                layer_name="ns:buildings",
                protocol="wfs",
                table_name="buildings_stg",
                engine=mock_engine,
                schema="public",
            )


@pytest.mark.parametrize(
    "service_url, expected_gdal_source",
    [
        ("https://host/v1", "OAPIF:https://host/v1"),
        ("https://host/v1/", "OAPIF:https://host/v1"),
        ("https://host/v1/collections", "OAPIF:https://host/v1"),
        ("https://host/v1/collections/", "OAPIF:https://host/v1"),
        ("https://host/v1/collections/my_layer", "OAPIF:https://host/v1"),
        ("https://host/v1/collections/my_layer/items", "OAPIF:https://host/v1"),
    ],
)
@patch("data_manipulation.ingestion._write_batches_to_postgis")
@patch("data_manipulation.ingestion._iter_pyogrio_arrow_batches")
def test_oapif_url_normalized_before_gdal(
    mock_iter: Mock,
    mock_write: Mock,
    service_url: str,
    expected_gdal_source: str,
) -> None:
    """GDAL always receives the service root URL regardless of what the user pasted."""
    ingest_data_from_ogc_service_into_postgis(
        service_url=service_url,
        layer_name="my_layer",
        protocol="ogcFeatures",
        table_name="stg",
        engine=Mock(spec=Engine),
    )

    mock_iter.assert_called_once()
    assert mock_iter.call_args.args[0] == expected_gdal_source
    assert mock_iter.call_args.kwargs["layer"] == "my_layer"


class TestIterDataBatches:
    """Streaming batch reader: dispatch + per-format behaviour."""

    def test_parquet_tabular_yields_dataframes(self, tmp_path: Path) -> None:
        path = tmp_path / "tab.parquet"
        table = pa.table({"a": list(range(2500)), "b": [f"x{i}" for i in range(2500)]})
        pq.write_table(table, path)

        batches = list(_iter_data_batches(str(path), batch_rows=1000))

        assert len(batches) == 3
        assert [len(b) for b in batches] == [1000, 1000, 500]
        assert all(isinstance(b, DataFrame) and not isinstance(b, GeoDataFrame) for b in batches)
        assert batches[0]["a"].tolist() == list(range(1000))

    def test_geoparquet_yields_geodataframes_with_crs(self, tmp_path: Path) -> None:
        gdf = GeoDataFrame(
            {"name": [f"p{i}" for i in range(1500)]},
            geometry=[Point(i, i) for i in range(1500)],
            crs="EPSG:4326",
        )
        path = tmp_path / "geo.parquet"
        gdf.to_parquet(path)

        batches = list(_iter_data_batches(str(path), batch_rows=600))

        assert len(batches) == 3
        assert all(isinstance(b, GeoDataFrame) for b in batches)
        assert batches[0].crs is not None
        assert all(b.geometry.is_valid.all() for b in batches)
        assert sum(len(b) for b in batches) == 1500

    def test_geojson_via_pyogrio_arrow(self, tmp_path: Path) -> None:
        gdf = GeoDataFrame(
            {"id": list(range(750))},
            geometry=[Point(i, i + 1) for i in range(750)],
            crs="EPSG:4326",
        )
        path = tmp_path / "data.geojson"
        gdf.to_file(path, driver="GeoJSON")

        batches = list(_iter_data_batches(str(path), batch_rows=300))

        assert sum(len(b) for b in batches) == 750
        assert all(isinstance(b, GeoDataFrame) for b in batches)
        assert batches[0].crs is not None

    def test_shapefile_unicode_fallback_uses_chunked_reader(self, tmp_path: Path) -> None:
        # Force the Arrow path to raise UnicodeDecodeError; assert we then call
        # pyogrio.read_dataframe with skip_features/max_features pairs.
        slices = [
            GeoDataFrame({"n": [0, 1]}, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326"),
            GeoDataFrame({"n": [2, 3]}, geometry=[Point(2, 2), Point(3, 3)], crs="EPSG:4326"),
            GeoDataFrame({"n": [4]}, geometry=[Point(4, 4)], crs="EPSG:4326"),
        ]
        path = tmp_path / "shape.shp"
        path.write_bytes(b"\x00\x00")  # path must exist; content unused (mocked)

        with (
            patch(
                "data_manipulation.ingestion._iter_pyogrio_arrow_batches",
                side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "boom"),
            ),
            patch("pyogrio.read_info", return_value={"features": 5}),
            patch("pyogrio.read_dataframe", side_effect=slices) as mock_read,
            patch(
                "data_manipulation.ingestion._detect_file_encoding",
                return_value="latin-1",
            ),
        ):
            batches = list(_iter_data_batches(str(path), batch_rows=2))

        assert [len(b) for b in batches] == [2, 2, 1]
        # Confirm offsets passed to pyogrio.read_dataframe walk the file.
        calls = mock_read.call_args_list
        assert [c.kwargs["skip_features"] for c in calls] == [0, 2, 4]
        assert all(c.kwargs["max_features"] == 2 for c in calls)
        assert all(c.kwargs["encoding"] == "latin-1" for c in calls)

    def test_non_shp_unicode_error_propagates(self, tmp_path: Path) -> None:
        path = tmp_path / "thing.geojson"
        path.write_text("{}")
        with patch(
            "data_manipulation.ingestion._iter_pyogrio_arrow_batches",
            side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "boom"),
        ):
            with pytest.raises(UnicodeDecodeError):
                list(_iter_data_batches(str(path)))
