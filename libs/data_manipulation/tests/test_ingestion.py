"""Tests for data ingestion utilities in data_manipulation library."""

from unittest.mock import MagicMock, Mock, patch

import geopandas as gpd
import pytest
import requests
from geopandas import GeoDataFrame
from pandas import DataFrame
from shapely.geometry import Point
from sqlalchemy.engine import Engine

from data_manipulation import IntegrityTransformation, apply_transformations
from data_manipulation.ingestion import (
    ingest_data_from_file_into_postgis,
    ingest_data_from_url_into_postgis,
    read_data_from_postgis,
    write_data_to_postgis,
)


class TestIngestDataFromFileIntoPostgis:
    """Test cases for ingest_data_from_file_into_postgis function."""

    @pytest.fixture
    def mock_engine(self) -> Mock:
        """Create a mock SQLAlchemy engine."""
        return Mock(spec=Engine)

    @patch("data_manipulation.ingestion.write_data_to_postgis")
    @patch("data_manipulation.ingestion.gpd.read_file")
    @patch("data_manipulation.ingestion._detect_file_encoding")
    def test_ingest_with_detected_encoding_success(
        self,
        mock_detect_encoding: Mock,
        mock_read_file: Mock,
        mock_write_data: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test successful ingestion with detected encoding."""

        mock_detect_encoding.return_value = "utf-8"
        mock_gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})
        mock_read_file.return_value = mock_gdf

        ingest_data_from_file_into_postgis("test.geojson", "test_table", mock_engine, "public")

        mock_detect_encoding.assert_called_once_with("test.geojson")
        mock_read_file.assert_called_once_with("test.geojson", encoding="utf-8")
        mock_write_data.assert_called_once_with(mock_gdf, "test_table", mock_engine, "public")

    @patch("data_manipulation.ingestion.write_data_to_postgis")
    @patch("data_manipulation.ingestion.gpd.read_file")
    @patch("data_manipulation.ingestion._detect_file_encoding")
    def test_ingest_with_encoding_fallback_to_latin1(
        self,
        mock_detect_encoding: Mock,
        mock_read_file: Mock,
        mock_write_data: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion falls back to latin-1 when UTF-8 fails."""

        mock_detect_encoding.return_value = "utf-8"
        mock_gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})

        # First call with utf-8 raises UnicodeDecodeError, second call with latin-1 succeeds
        mock_read_file.side_effect = [UnicodeDecodeError("utf-8", b"", 0, 1, ""), mock_gdf]

        ingest_data_from_file_into_postgis("test.geojson", "test_table", mock_engine, "public")

        assert mock_read_file.call_count == 2
        mock_read_file.assert_any_call("test.geojson", encoding="utf-8")
        mock_read_file.assert_any_call("test.geojson", encoding="latin-1")
        mock_write_data.assert_called_once_with(mock_gdf, "test_table", mock_engine, "public")

    @patch("data_manipulation.ingestion.write_data_to_postgis")
    @patch("data_manipulation.ingestion.gpd.read_file")
    @patch("data_manipulation.ingestion._detect_file_encoding")
    def test_ingest_with_encoding_fallback_to_cp1252(
        self,
        mock_detect_encoding: Mock,
        mock_read_file: Mock,
        mock_write_data: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion falls back to cp1252 when UTF-8 and latin-1 fail."""

        mock_detect_encoding.return_value = "utf-8"
        mock_gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})

        # First two calls fail, third call with cp1252 succeeds
        mock_read_file.side_effect = [
            UnicodeDecodeError("utf-8", b"", 0, 1, ""),
            UnicodeDecodeError("latin-1", b"", 0, 1, ""),
            mock_gdf,
        ]

        ingest_data_from_file_into_postgis("test.geojson", "test_table", mock_engine, "public")

        assert mock_read_file.call_count == 3
        mock_read_file.assert_any_call("test.geojson", encoding="utf-8")
        mock_read_file.assert_any_call("test.geojson", encoding="latin-1")
        mock_read_file.assert_any_call("test.geojson", encoding="cp1252")
        mock_write_data.assert_called_once_with(mock_gdf, "test_table", mock_engine, "public")

    @patch("data_manipulation.ingestion.gpd.read_file")
    @patch("data_manipulation.ingestion._detect_file_encoding")
    def test_ingest_raises_exception_on_error(
        self,
        mock_detect_encoding: Mock,
        mock_read_file: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion raises exception when all encoding attempts fail."""

        mock_detect_encoding.return_value = "utf-8"
        mock_read_file.side_effect = Exception("Failed to read file")

        with pytest.raises(Exception, match="Failed to read file"):
            ingest_data_from_file_into_postgis("test.geojson", "test_table", mock_engine, "public")


class TestIngestDataFromUrlIntoPostgis:
    """Test cases for ingest_data_from_url_into_postgis function."""

    @pytest.fixture
    def mock_engine(self) -> Mock:
        """Create a mock SQLAlchemy engine."""
        return Mock(spec=Engine)

    @patch("data_manipulation.ingestion.write_data_to_postgis")
    @patch("data_manipulation.ingestion.gpd.read_file")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_success(
        self,
        mock_requests_get: Mock,
        mock_read_file: Mock,
        mock_write_data: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test successful ingestion from URL."""

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test data"
        mock_response.headers = {}
        mock_requests_get.return_value = mock_response

        # Mock the GeoDataFrame
        mock_gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})
        mock_read_file.return_value = mock_gdf

        ingest_data_from_url_into_postgis(
            "http://example.com/data.geojson", "test_table", mock_engine, "public"
        )

        mock_requests_get.assert_called_once_with(
            "http://example.com/data.geojson", auth=None, timeout=300
        )
        mock_read_file.assert_called_once()
        mock_write_data.assert_called_once_with(mock_gdf, "test_table", mock_engine, "public")

    @patch("data_manipulation.ingestion.write_data_to_postgis")
    @patch("data_manipulation.ingestion.gpd.read_file")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_with_auth(
        self,
        mock_requests_get: Mock,
        mock_read_file: Mock,
        mock_write_data: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion from URL with authentication."""

        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test data"
        mock_response.headers = {}
        mock_requests_get.return_value = mock_response

        # Mock the GeoDataFrame
        mock_gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})
        mock_read_file.return_value = mock_gdf

        auth = ("username", "password")
        ingest_data_from_url_into_postgis(
            "http://example.com/data.geojson", "test_table", mock_engine, "public", auth=auth
        )

        mock_requests_get.assert_called_once_with(
            "http://example.com/data.geojson", auth=auth, timeout=300
        )

    @patch("data_manipulation.ingestion.write_data_to_postgis")
    @patch("data_manipulation.ingestion.gpd.read_file")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_with_content_disposition(
        self,
        mock_requests_get: Mock,
        mock_read_file: Mock,
        mock_write_data: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion from URL extracts filename from Content-Disposition."""

        # Mock the HTTP response with Content-Disposition header
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test data"
        mock_response.headers = {"Content-Disposition": 'attachment; filename="data.geojson"'}
        mock_requests_get.return_value = mock_response

        # Mock the GeoDataFrame
        mock_gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})
        mock_read_file.return_value = mock_gdf

        ingest_data_from_url_into_postgis(
            "http://example.com/download", "test_table", mock_engine, "public"
        )

        mock_requests_get.assert_called_once()
        mock_read_file.assert_called_once()
        # Verify that the file was saved with the extracted filename
        call_args = mock_read_file.call_args[0][0]
        assert "data.geojson" in str(call_args)

    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_http_error(
        self,
        mock_requests_get: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test ingestion from URL raises exception on HTTP error."""

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
        """Test ingestion from URL raises exception on connection error."""

        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(requests.exceptions.ConnectionError):
            ingest_data_from_url_into_postgis(
                "http://example.com/data.geojson", "test_table", mock_engine, "public"
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


class TestWriteDataToPostgis:
    """Test cases for write_data_to_postgis function."""

    @pytest.fixture
    def mock_engine(self) -> Mock:
        """Create a mock SQLAlchemy engine."""
        return Mock(spec=Engine)

    @patch("data_manipulation.ingestion._get_table_row_count")
    def test_write_geodataframe_with_geom_column(
        self,
        mock_get_row_count: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test writing GeoDataFrame with 'geom' as active geometry."""

        gdf = GeoDataFrame(
            {"col1": [1, 2]},
            geometry=gpd.GeoSeries([Point(0, 0), Point(1, 1)], name="geom"),
        )
        mock_get_row_count.return_value = 2

        with patch.object(gdf, "to_postgis") as mock_to_postgis:
            write_data_to_postgis(gdf, "test_table", mock_engine, "public")

            mock_to_postgis.assert_called_once_with(
                "test_table", mock_engine, if_exists="replace", schema="public", index=False
            )

    @patch("data_manipulation.ingestion._get_table_row_count")
    def test_write_geodataframe_renames_geometry_column(
        self,
        mock_get_row_count: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test writing GeoDataFrame renames geometry column to 'geom'."""

        gdf = GeoDataFrame(
            {"col1": [1, 2]},
            geometry=gpd.GeoSeries([Point(0, 0), Point(1, 1)], name="geometry"),
        )
        mock_get_row_count.return_value = 2

        with patch.object(gdf, "to_postgis") as mock_to_postgis:
            write_data_to_postgis(gdf, "test_table", mock_engine, "public")

            # Should have been renamed to 'geom'
            assert gdf.geometry.name == "geom"
            mock_to_postgis.assert_called_once()

    @patch("data_manipulation.ingestion._get_table_row_count")
    def test_write_geodataframe_without_geometry(
        self,
        mock_get_row_count: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test writing GeoDataFrame without active geometry column."""

        # Create a GeoDataFrame but set geometry to None
        gdf = GeoDataFrame({"col1": [1, 2], "col2": [3, 4]})
        gdf._geometry_column_name = None
        mock_get_row_count.return_value = 2

        with patch.object(gdf, "to_postgis") as mock_to_postgis:
            write_data_to_postgis(gdf, "test_table", mock_engine, "public")

            mock_to_postgis.assert_called_once()

    @patch("data_manipulation.ingestion._get_table_row_count")
    def test_write_dataframe_without_geometry(
        self,
        mock_get_row_count: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test writing regular DataFrame (non-geographic data)."""

        df = DataFrame({"col1": [1, 2], "col2": [3, 4]})
        mock_get_row_count.return_value = 2

        with patch.object(df, "to_sql") as mock_to_sql:
            write_data_to_postgis(df, "test_table", mock_engine, "public")

            mock_to_sql.assert_called_once_with(
                "test_table", mock_engine, if_exists="replace", schema="public", index=False
            )

    @patch("data_manipulation.ingestion._get_table_row_count")
    def test_write_dataframe_removes_geom_column_if_present(
        self,
        mock_get_row_count: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test that DataFrame with 'geom' column has it removed."""

        df = DataFrame({"col1": [1, 2], "geom": ["point1", "point2"]})
        mock_get_row_count.return_value = 2

        with patch("pandas.DataFrame.to_sql", return_value=None) as mock_to_sql:
            write_data_to_postgis(df, "test_table", mock_engine, "public")

            # Verify to_sql was called
            mock_to_sql.assert_called_once()

            # Verify the instance has the columns we expect
            assert "geom" not in df.columns, "geom column should have been removed"
            assert "col1" in df.columns, "col1 column should still be present"

    def test_write_validates_table_name(self, mock_engine: Mock) -> None:
        """Test that write_data validates table name."""

        gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})

        with pytest.raises(ValueError):
            write_data_to_postgis(gdf, "invalid-table-name!", mock_engine, "public")

    def test_write_sql_injection_prevented(self, mock_engine: Mock) -> None:
        """Test that SQL injection attempts are prevented."""

        gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})
        malicious_names = [
            "table; DROP TABLE users--",
            "table' OR '1'='1",
            'table" DROP SCHEMA public CASCADE--',
        ]

        for malicious_name in malicious_names:
            with pytest.raises(ValueError):
                write_data_to_postgis(gdf, malicious_name, mock_engine, "public")

    @patch("data_manipulation.ingestion._get_table_row_count")
    def test_write_logs_row_count(
        self,
        mock_get_row_count: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test that row count is logged after successful write."""

        gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})
        mock_get_row_count.return_value = 2

        with patch.object(gdf, "to_postgis"):
            write_data_to_postgis(gdf, "test_table", mock_engine, "public")

            mock_get_row_count.assert_called_once_with("test_table", mock_engine, "public")

    @patch("data_manipulation.ingestion._get_table_row_count")
    def test_write_raises_exception_on_error(
        self,
        mock_get_row_count: Mock,
        mock_engine: Mock,
    ) -> None:
        """Test that errors during writing are raised."""

        gdf = GeoDataFrame({"col1": [1, 2], "geometry": [Point(0, 0), Point(1, 1)]})

        with patch.object(gdf, "to_postgis", side_effect=Exception("Write failed")):
            with pytest.raises(Exception, match="Write failed"):
                write_data_to_postgis(gdf, "test_table", mock_engine, "public")
