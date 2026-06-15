"""Tests for data ingestion orchestrators in data_manipulation library."""

from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch
from urllib.error import URLError

import pytest
import requests
from sqlalchemy.engine import Engine

from data_manipulation.ingestion import (
    ingest_data_from_database_into_postgis,
    ingest_data_from_file_into_postgis,
    ingest_data_from_ftp_into_postgis,
    ingest_data_from_ogc_service_into_postgis,
    ingest_data_from_url_into_postgis,
)


@contextmanager
def _cm(value: object):
    """Trivial context manager yielding ``value`` (stands in for open_* helpers)."""
    yield value


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

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_file")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_success(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_open_file: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response()
        sentinel = object()
        mock_open_file.return_value = _cm(sentinel)

        ingest_data_from_url_into_postgis(
            "http://example.com/data.geojson", "test_table", mock_engine, "public"
        )

        mock_requests_get.assert_called_once_with(
            "http://example.com/data.geojson", auth=None, timeout=(10, 300), stream=True
        )
        mock_open_file.assert_called_once()
        mock_writer.assert_called_once_with(sentinel, "test_table", mock_engine, schema="public")

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_file")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_with_auth(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_open_file: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response()
        mock_open_file.return_value = _cm(object())
        auth = ("username", "password")
        ingest_data_from_url_into_postgis(
            "http://example.com/data.geojson", "test_table", mock_engine, "public", auth=auth
        )
        mock_requests_get.assert_called_once_with(
            "http://example.com/data.geojson", auth=auth, timeout=(10, 300), stream=True
        )

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_file")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_from_url_with_content_disposition(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_open_file: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response(
            {"Content-Disposition": 'attachment; filename="data.geojson"'}
        )
        mock_open_file.return_value = _cm(object())

        ingest_data_from_url_into_postgis(
            "http://example.com/download", "test_table", mock_engine, "public"
        )

        # The downloaded temp file's name is derived from Content-Disposition.
        path_arg = mock_open_file.call_args.args[0]
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

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_file")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_parquet_url_by_extension(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_open_file: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response()
        mock_open_file.return_value = _cm(object())
        ingest_data_from_url_into_postgis(
            "http://example.com/layer.parquet", "test_table", mock_engine, "public"
        )
        path_arg = mock_open_file.call_args.args[0]
        assert str(path_arg).endswith(".parquet")
        mock_writer.assert_called_once()

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_file")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_ingest_parquet_url_with_content_disposition(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_open_file: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_requests_get.return_value = self._make_response(
            {"Content-Disposition": 'attachment; filename="export.parquet"'}
        )
        mock_open_file.return_value = _cm(object())
        ingest_data_from_url_into_postgis(
            "http://example.com/download/42", "test_table", mock_engine, "public"
        )
        path_arg = mock_open_file.call_args.args[0]
        assert str(path_arg).endswith("export.parquet")

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_file")
    @patch("data_manipulation.ingestion.detect_file_encoding", return_value="latin-1")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_shapefile_unicode_decode_retries_with_encoding(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_detect: Mock,
        mock_open_file: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        """A UnicodeDecodeError on a .shp triggers a full retry with detected encoding."""
        mock_requests_get.return_value = self._make_response(
            {"Content-Disposition": 'attachment; filename="layer.shp"'}
        )
        first = object()
        second = object()
        mock_open_file.side_effect = [_cm(first), _cm(second)]
        mock_writer.side_effect = [
            UnicodeDecodeError("utf-8", b"", 0, 1, "boom"),
            42,
        ]

        ingest_data_from_url_into_postgis(
            "http://example.com/download", "test_table", mock_engine, "public"
        )

        # open_file called twice: bare first, then with encoding.
        assert mock_open_file.call_count == 2
        assert mock_open_file.call_args_list[0].kwargs == {}
        assert mock_open_file.call_args_list[1].kwargs == {"encoding": "latin-1"}
        # Writer called twice, second time with the retried source.
        assert mock_writer.call_count == 2
        assert mock_writer.call_args_list[1].args[0] is second

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_file")
    @patch("data_manipulation.ingestion.shutil.copyfileobj")
    @patch("data_manipulation.ingestion.requests.get")
    def test_non_shp_unicode_decode_propagates(
        self,
        mock_requests_get: Mock,
        mock_copyfileobj: Mock,
        mock_open_file: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        """A UnicodeDecodeError on a non-shapefile is not retried — it propagates."""
        mock_requests_get.return_value = self._make_response(
            {"Content-Disposition": 'attachment; filename="data.geojson"'}
        )
        mock_open_file.return_value = _cm(object())
        mock_writer.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "boom")

        with pytest.raises(UnicodeDecodeError):
            ingest_data_from_url_into_postgis(
                "http://example.com/download", "test_table", mock_engine, "public"
            )
        assert mock_open_file.call_count == 1


class TestIngestDataFromFtpIntoPostgis:
    """Test cases for ingest_data_from_ftp_into_postgis function."""

    @pytest.fixture
    def mock_engine(self) -> Mock:
        """Create a mock SQLAlchemy engine."""
        return Mock(spec=Engine)

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_file")
    @patch("data_manipulation.ingestion.urlretrieve")
    def test_ingest_from_ftp_success(
        self,
        mock_urlretrieve: Mock,
        mock_open_file: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        sentinel = object()
        mock_open_file.return_value = _cm(sentinel)

        ingest_data_from_ftp_into_postgis(
            "ftp://example.com/data.geojson", "test_table", mock_engine, "public"
        )

        mock_urlretrieve.assert_called_once()
        assert "ftp://example.com/data.geojson" in str(mock_urlretrieve.call_args[0][0])
        mock_open_file.assert_called_once()
        mock_writer.assert_called_once_with(sentinel, "test_table", mock_engine, schema="public")

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_file")
    @patch("data_manipulation.ingestion.urlretrieve")
    def test_ingest_from_ftp_with_auth(
        self,
        mock_urlretrieve: Mock,
        mock_open_file: Mock,
        mock_writer: Mock,
        mock_engine: Mock,
    ) -> None:
        mock_open_file.return_value = _cm(object())
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


class TestIngestDataFromDatabaseIntoPostgis:
    """Test cases for ingest_data_from_database_into_postgis function."""

    @pytest.fixture
    def mock_source_engine(self) -> Mock:
        return Mock(spec=Engine)

    @pytest.fixture
    def mock_target_engine(self) -> Mock:
        return Mock(spec=Engine)

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_postgis_table")
    def test_wires_open_postgis_table_to_writer(
        self,
        mock_open_table: Mock,
        mock_writer: Mock,
        mock_source_engine: Mock,
        mock_target_engine: Mock,
    ) -> None:
        """The source table is opened and handed straight to the ADBC writer."""
        sentinel = object()
        mock_open_table.return_value = _cm(sentinel)

        ingest_data_from_database_into_postgis(
            source_schema="public",
            source_table="communes",
            source_engine=mock_source_engine,
            target_table="staging_table",
            target_engine=mock_target_engine,
            target_schema="staging",
        )

        mock_open_table.assert_called_once_with("communes", "public", mock_source_engine)
        mock_writer.assert_called_once_with(
            sentinel, "staging_table", mock_target_engine, schema="staging"
        )

    @patch("data_manipulation.ingestion.open_postgis_table")
    def test_source_table_not_found_raises(
        self,
        mock_open_table: Mock,
        mock_source_engine: Mock,
        mock_target_engine: Mock,
    ) -> None:
        """Exception is raised when source table does not exist."""
        mock_open_table.side_effect = Exception("Table not found")

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

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_ogr")
    def test_wfs_uses_wfs_gdal_prefix(
        self,
        mock_open_ogr: Mock,
        mock_write: Mock,
        mock_engine: Mock,
    ) -> None:
        """WFS protocol produces a WFS: prefixed GDAL source string."""
        sentinel = object()
        mock_open_ogr.return_value = _cm(sentinel)

        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.com/wfs",
            layer_name="ns:buildings",
            protocol="wfs",
            table_name="buildings_stg",
            engine=mock_engine,
            schema="public",
        )

        assert mock_open_ogr.call_args.args[0] == "WFS:https://example.com/wfs"
        assert mock_open_ogr.call_args.kwargs["layer"] == "ns:buildings"
        mock_write.assert_called_once_with(sentinel, "buildings_stg", mock_engine, schema="public")

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_ogr")
    def test_ogc_api_features_uses_oapif_gdal_prefix(
        self,
        mock_open_ogr: Mock,
        mock_write: Mock,
        mock_engine: Mock,
    ) -> None:
        """ogcFeatures protocol produces an OAPIF: prefixed GDAL source string."""
        mock_open_ogr.return_value = _cm(object())
        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.com/ogcapi",
            layer_name="parcels",
            protocol="ogcFeatures",
            table_name="parcels_stg",
            engine=mock_engine,
            schema="public",
        )

        assert mock_open_ogr.call_args.args[0] == "OAPIF:https://example.com/ogcapi"
        assert mock_open_ogr.call_args.kwargs["layer"] == "parcels"
        mock_write.assert_called_once()

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_ogr")
    def test_unknown_protocol_falls_back_to_wfs_prefix(
        self,
        mock_open_ogr: Mock,
        mock_write: Mock,
        mock_engine: Mock,
    ) -> None:
        """Unknown protocol value falls back to the WFS: GDAL prefix."""
        mock_open_ogr.return_value = _cm(object())
        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.com/wfs",
            layer_name="ns:rivers",
            protocol="unknown_protocol",
            table_name="rivers_stg",
            engine=mock_engine,
            schema="public",
        )

        assert mock_open_ogr.call_args.args[0].startswith("WFS:")

    @patch("data_manipulation.ingestion.write_arrow_to_postgis")
    @patch("data_manipulation.ingestion.open_ogr")
    def test_read_exception_is_reraised(
        self,
        mock_open_ogr: Mock,
        mock_write: Mock,
        mock_engine: Mock,
    ) -> None:
        """Exceptions raised while writing the layer are propagated to the caller."""
        mock_open_ogr.return_value = _cm(object())
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
@patch("data_manipulation.ingestion.write_arrow_to_postgis")
@patch("data_manipulation.ingestion.open_ogr")
def test_oapif_url_normalized_before_gdal(
    mock_open_ogr: Mock,
    mock_write: Mock,
    service_url: str,
    expected_gdal_source: str,
) -> None:
    """GDAL always receives the service root URL regardless of what the user pasted."""
    mock_open_ogr.return_value = _cm(object())
    ingest_data_from_ogc_service_into_postgis(
        service_url=service_url,
        layer_name="my_layer",
        protocol="ogcFeatures",
        table_name="stg",
        engine=Mock(spec=Engine),
    )

    mock_open_ogr.assert_called_once()
    assert mock_open_ogr.call_args.args[0] == expected_gdal_source
    assert mock_open_ogr.call_args.kwargs["layer"] == "my_layer"
