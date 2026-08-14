"""Tests for ogr2ogr-based ingestion.

``ogr2ogr``/GDAL is not installed in the unit-test environment, so every test
mocks ``subprocess.run`` (and the network helpers) and asserts on the command
that *would* be executed.  Full integration runs in the Docker image.
"""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from data_manipulation.ingestion import (
    _build_pg_connection_string,  # type: ignore[reportPrivateUsage]
    _normalize_oapif_url,  # type: ignore[reportPrivateUsage]
    ingest_data_from_database_into_postgis,
    ingest_data_from_ftp_into_postgis,
    ingest_data_from_ogc_service_into_postgis,
    ingest_file_with_ogr2ogr,
)


@pytest.fixture
def engine() -> Engine:
    # Engine creation does not open a connection; safe to use a fake URL.
    return create_engine("postgresql://user:secret@dbhost:5432/datadb")


@pytest.fixture
def source_engine() -> Engine:
    return create_engine("postgresql://srcuser:srcpass@srchost:5433/srcdb")


def _completed() -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["ogr2ogr"], returncode=0, stdout="", stderr="")


class TestPgConnectionString:
    def test_contains_all_parts(self, engine: Engine) -> None:
        conn = _build_pg_connection_string(engine)
        assert conn.startswith("PG:")
        assert "host=dbhost" in conn
        assert "port=5432" in conn
        assert "dbname=datadb" in conn
        assert "user=user" in conn
        assert "password=secret" in conn


class TestNormalizeOapifUrl:
    def test_strips_collections_suffix(self) -> None:
        assert _normalize_oapif_url("https://x/ogcapi/collections/buildings") == "https://x/ogcapi"

    def test_strips_trailing_collections(self) -> None:
        assert _normalize_oapif_url("https://x/ogcapi/collections") == "https://x/ogcapi"

    def test_leaves_plain_root_untouched(self) -> None:
        assert _normalize_oapif_url("https://x/ogcapi") == "https://x/ogcapi"


class TestIngestFileWithOgr2ogr:
    @patch("data_manipulation.ingestion.subprocess.run")
    def test_builds_expected_command(self, mock_run: MagicMock, engine: Engine) -> None:
        mock_run.return_value = _completed()
        ingest_file_with_ogr2ogr("/tmp/data.geojson", "places", engine, schema="staging")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ogr2ogr"
        assert "-f" in cmd and "PostgreSQL" in cmd
        assert "/tmp/data.geojson" in cmd
        assert "staging.places" in cmd
        assert "-overwrite" in cmd
        assert "GEOMETRY_NAME=geom" in cmd

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_missing_binary_raises_clean_error(self, mock_run: MagicMock, engine: Engine) -> None:
        mock_run.side_effect = FileNotFoundError()
        with pytest.raises(Exception, match="ogr2ogr"):
            ingest_file_with_ogr2ogr("/tmp/data.geojson", "places", engine)

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_ogr_failure_surfaces_stderr(self, mock_run: MagicMock, engine: Engine) -> None:
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd=["ogr2ogr"], stderr="bad data"
        )
        with pytest.raises(Exception, match="bad data"):
            ingest_file_with_ogr2ogr("/tmp/data.geojson", "places", engine)


class TestIngestFromDatabase:
    @patch("data_manipulation.ingestion.subprocess.run")
    def test_streams_pg_to_pg(
        self, mock_run: MagicMock, engine: Engine, source_engine: Engine
    ) -> None:
        mock_run.return_value = _completed()
        ingest_data_from_database_into_postgis(
            source_schema="public",
            source_table="src",
            source_engine=source_engine,
            target_table="dest",
            target_engine=engine,
            target_schema="staging",
        )
        cmd = mock_run.call_args[0][0]
        # both PG connection strings present
        assert any(c.startswith("PG:") and "srchost" in c for c in cmd)
        assert any(c.startswith("PG:") and "dbhost" in c for c in cmd)
        assert "public.src" in cmd
        assert "staging.dest" in cmd


class TestIngestFromOgcService:
    @patch("data_manipulation.ingestion.subprocess.run")
    def test_wfs_prefix(self, mock_run: MagicMock, engine: Engine) -> None:
        mock_run.return_value = _completed()
        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.org/wfs",
            layer_name="ns:buildings",
            protocol="wfs",
            table_name="places",
            engine=engine,
            schema="staging",
        )
        cmd = mock_run.call_args[0][0]
        assert "WFS:https://example.org/wfs" in cmd
        assert "ns:buildings" in cmd

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_oapif_prefix_and_normalized_url(self, mock_run: MagicMock, engine: Engine) -> None:
        mock_run.return_value = _completed()
        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.org/ogcapi/collections/buildings",
            layer_name="buildings",
            protocol="ogcFeatures",
            table_name="places",
            engine=engine,
        )
        cmd = mock_run.call_args[0][0]
        assert "OAPIF:https://example.org/ogcapi" in cmd

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_auth_passed_via_gdal_config(self, mock_run: MagicMock, engine: Engine) -> None:
        mock_run.return_value = _completed()
        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.org/wfs",
            layer_name="ns:buildings",
            protocol="wfs",
            table_name="places",
            engine=engine,
            auth=("alice", "s3cret"),
        )
        cmd = mock_run.call_args[0][0]
        assert "--config" in cmd
        assert "GDAL_HTTP_USERPWD" in cmd
        assert "alice:s3cret" in cmd

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_no_auth_means_no_userpwd(self, mock_run: MagicMock, engine: Engine) -> None:
        mock_run.return_value = _completed()
        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.org/wfs",
            layer_name="ns:buildings",
            protocol="wfs",
            table_name="places",
            engine=engine,
        )
        cmd = mock_run.call_args[0][0]
        assert "GDAL_HTTP_USERPWD" not in cmd


class TestIngestFromFtp:
    @patch("data_manipulation.ingestion.ingest_file_with_ogr2ogr")
    @patch("data_manipulation.ingestion.urlretrieve")
    def test_builds_credentialed_url(
        self, mock_retrieve: MagicMock, mock_ingest: MagicMock, engine: Engine
    ) -> None:
        ingest_data_from_ftp_into_postgis(
            "ftp://ftp.example.org/data/file.gpkg",
            "places",
            engine,
            auth=("bob", "pw@ss"),
        )
        # urlretrieve gets a credentialed URL (password URL-encoded)
        called_url = mock_retrieve.call_args[0][0]
        assert called_url.startswith("ftp://bob:")
        assert "pw%40ss" in called_url
        mock_ingest.assert_called_once()
