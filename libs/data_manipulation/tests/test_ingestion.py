"""Tests for ogr2ogr-based ingestion.

``ogr2ogr``/GDAL is not installed in the unit-test environment, so every test
mocks ``subprocess.run`` (and the network helpers) and asserts on the command
that *would* be executed.  Full integration runs in the Docker image.
"""

import logging
import struct
import subprocess
import zipfile
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from data_manipulation.ingestion import (
    _build_pg_connection_string,  # type: ignore[reportPrivateUsage]
    _detect_shapefile_encoding,  # type: ignore[reportPrivateUsage]
    _normalize_oapif_url,  # type: ignore[reportPrivateUsage]
    _resolve_zip_source,  # type: ignore[reportPrivateUsage]
    ingest_data_from_database_into_postgis,
    ingest_data_from_ftp_into_postgis,
    ingest_data_from_ogc_service_into_postgis,
    ingest_data_from_url_into_postgis,
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


class TestNoCredentialLogging:
    """The ogr2ogr argv embeds PG passwords and GDAL_HTTP_USERPWD: never log it."""

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_file_ingest_does_not_log_password(
        self, mock_run: MagicMock, engine: Engine, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_run.return_value = _completed()
        with caplog.at_level(logging.DEBUG, logger="data_manipulation.ingestion"):
            ingest_file_with_ogr2ogr("/tmp/data.geojson", "places", engine, schema="staging")
        assert "secret" not in caplog.text

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_db_ingest_does_not_log_passwords(
        self,
        mock_run: MagicMock,
        engine: Engine,
        source_engine: Engine,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        mock_run.return_value = _completed()
        with caplog.at_level(logging.DEBUG, logger="data_manipulation.ingestion"):
            ingest_data_from_database_into_postgis(
                "public", "src", source_engine, "dst", engine, "staging"
            )
        assert "secret" not in caplog.text
        assert "srcpass" not in caplog.text

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_ogc_ingest_does_not_log_auth(
        self, mock_run: MagicMock, engine: Engine, caplog: pytest.LogCaptureFixture
    ) -> None:
        mock_run.return_value = _completed()
        with caplog.at_level(logging.DEBUG, logger="data_manipulation.ingestion"):
            ingest_data_from_ogc_service_into_postgis(
                "wfs",
                "https://example.org/wfs",
                "ns:buildings",
                "places",
                engine,
                schema="staging",
                auth=("wfsuser", "wfspass"),
            )
        assert "secret" not in caplog.text
        assert "wfspass" not in caplog.text


def _make_zip(path: Path, members: list[str]) -> str:
    """Write a ZIP containing *members* (empty files) and return its path."""
    with zipfile.ZipFile(path, "w") as archive:
        for member in members:
            archive.writestr(member, b"")
    return str(path)


_SHAPEFILE_MEMBERS = ["pts.shp", "pts.shx", "pts.dbf", "pts.prj", "pts.cpg"]


class TestResolveZipSource:
    """GDAL cannot open a .zip by plain path; it needs the /vsizip/ prefix.

    Verified against GDAL 3.12: ogr.Open("x.zip") raises "not recognized as
    being in a supported file format", while /vsizip/x.zip succeeds.
    """

    def test_plain_file_is_untouched(self, tmp_path: Path) -> None:
        plain = tmp_path / "data.gpkg"
        plain.write_bytes(b"not a zip")
        assert _resolve_zip_source(str(plain)) == str(plain)

    def test_shapefile_at_archive_root_gets_vsizip_prefix(self, tmp_path: Path) -> None:
        archive = _make_zip(tmp_path / "places.zip", _SHAPEFILE_MEMBERS)
        assert _resolve_zip_source(archive) == f"/vsizip/{archive}"

    def test_shapefile_in_subdirectory_includes_that_subdirectory(self, tmp_path: Path) -> None:
        # /vsizip/<zip> alone fails here — the subdirectory must be in the path.
        archive = _make_zip(tmp_path / "nested.zip", [f"data/{m}" for m in _SHAPEFILE_MEMBERS])
        assert _resolve_zip_source(archive) == f"/vsizip/{archive}/data"

    def test_sidecars_do_not_count_as_separate_datasets(self, tmp_path: Path) -> None:
        # .shx/.dbf/.prj/.cpg belong to the single pts dataset.
        archive = _make_zip(tmp_path / "one.zip", _SHAPEFILE_MEMBERS)
        assert _resolve_zip_source(archive).startswith("/vsizip/")

    def test_single_non_shapefile_dataset_is_accepted(self, tmp_path: Path) -> None:
        archive = _make_zip(tmp_path / "gpkg.zip", ["export.gpkg"])
        assert _resolve_zip_source(archive) == f"/vsizip/{archive}"

    def test_multiple_datasets_raise_instead_of_losing_data(self, tmp_path: Path) -> None:
        # ogr2ogr -nln writes every layer into the same table, so with
        # -overwrite each layer would silently replace the previous one.
        archive = _make_zip(
            tmp_path / "multi.zip", _SHAPEFILE_MEMBERS + ["second.shp", "second.dbf"]
        )
        with pytest.raises(Exception, match="multiple datasets"):
            _resolve_zip_source(archive)

    def test_multiple_datasets_error_names_them(self, tmp_path: Path) -> None:
        archive = _make_zip(
            tmp_path / "multi.zip", _SHAPEFILE_MEMBERS + ["second.shp", "second.dbf"]
        )
        with pytest.raises(Exception) as excinfo:
            _resolve_zip_source(archive)
        # The user has to know which layer to extract.
        assert "pts" in str(excinfo.value) and "second" in str(excinfo.value)

    def test_empty_archive_raises(self, tmp_path: Path) -> None:
        archive = _make_zip(tmp_path / "empty.zip", [])
        with pytest.raises(Exception, match="No geospatial dataset"):
            _resolve_zip_source(archive)

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_ogr2ogr_receives_the_vsizip_path(
        self, mock_run: MagicMock, engine: Engine, tmp_path: Path
    ) -> None:
        archive = _make_zip(tmp_path / "places.zip", _SHAPEFILE_MEMBERS)
        mock_run.return_value = _completed()

        ingest_file_with_ogr2ogr(archive, "places", engine, schema="staging")

        assert f"/vsizip/{archive}" in mock_run.call_args[0][0]


def _identity_url(url: str) -> str:
    """Stand in for resolve_url (which would hit the network) in tests."""
    return url


class _FakeResponse:
    """Minimal stand-in for a streamed ``requests`` response.

    ``content`` raises so a test fails loudly if the download ever buffers the
    whole body in memory again instead of streaming it to disk.
    """

    def __init__(self, chunks: list[bytes], headers: dict[str, str] | None = None) -> None:
        self._chunks = chunks
        self.headers = headers or {}
        self.iter_content_calls: list[int | None] = []

    @property
    def content(self) -> bytes:
        raise AssertionError("response.content read: the download must be streamed")

    def raise_for_status(self) -> None:
        pass

    def iter_content(self, chunk_size: int | None = None) -> Iterator[bytes]:
        self.iter_content_calls.append(chunk_size)
        yield from self._chunks

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class TestUrlDownloadIsStreamed:
    @patch("data_manipulation.ingestion.ingest_file_with_ogr2ogr")
    @patch("data_manipulation.ingestion.resolve_url", side_effect=_identity_url)
    @patch("data_manipulation.ingestion.requests.get")
    def test_streams_body_to_disk_without_buffering(
        self,
        mock_get: MagicMock,
        _resolve: MagicMock,
        mock_ingest: MagicMock,
        engine: Engine,
    ) -> None:
        response = _FakeResponse([b"abc", b"def"])
        mock_get.return_value = response

        written: dict[str, bytes] = {}

        def _capture(path: str, *args: object, **kwargs: object) -> None:
            written["data"] = Path(path).read_bytes()

        mock_ingest.side_effect = _capture

        ingest_data_from_url_into_postgis(
            "https://example.org/data.geojson", "places", engine, schema="staging"
        )

        # stream=True is what keeps requests from materialising the whole body.
        assert mock_get.call_args.kwargs["stream"] is True
        assert response.iter_content_calls, "body was not streamed via iter_content"
        # Chunks are reassembled verbatim on disk.
        assert written["data"] == b"abcdef"

    @patch("data_manipulation.ingestion.ingest_file_with_ogr2ogr")
    @patch("data_manipulation.ingestion.resolve_url", side_effect=_identity_url)
    @patch("data_manipulation.ingestion.requests.get")
    def test_content_disposition_still_names_the_file(
        self,
        mock_get: MagicMock,
        _resolve: MagicMock,
        mock_ingest: MagicMock,
        engine: Engine,
    ) -> None:
        # Headers must remain readable before the body is consumed.
        mock_get.return_value = _FakeResponse(
            [b"x"], headers={"Content-Disposition": 'attachment; filename="report.geojson"'}
        )

        ingest_data_from_url_into_postgis(
            "https://example.org/download?id=7", "places", engine, schema="staging"
        )

        assert Path(mock_ingest.call_args[0][0]).name == "report.geojson"


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
        assert "SCHEMA=staging" in cmd
        # NOT NULL constraints from the source layer (e.g. WFS gml_id) must not
        # be propagated, otherwise COPY fails when the value is absent.
        assert "-forceNullable" in cmd
        # Single geometries must be promoted to Multi* so a later feature that
        # happens to be a Multi* type doesn't clash with the inferred column type.
        assert "-nlt" in cmd
        assert "PROMOTE_TO_MULTI" in cmd

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
        assert "-nlt" in cmd
        assert "PROMOTE_TO_MULTI" in cmd


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
        # WFS layers frequently declare gml_id NOT NULL while the GeoJSON output
        # leaves it empty; the constraint must be dropped on the staging table.
        assert "-forceNullable" in cmd
        # A WFS serves whatever srsName was negotiated — commonly a projected CRS
        # such as EPSG:2154. Since -a_srs relabels without reprojecting, forcing
        # 4326 here would tag metric coordinates as degrees and silently move the
        # data. Keep the SRS advertised by the service.
        assert "-a_srs" not in cmd

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
    def test_oapif_assigns_wgs84(self, mock_run: MagicMock, engine: Engine) -> None:
        # OAPIF serves GeoJSON, which RFC 7946 pins to WGS84 lon/lat, and GDAL may
        # leave the geometry at SRID 0 — assigning 4326 is both safe and needed.
        mock_run.return_value = _completed()
        ingest_data_from_ogc_service_into_postgis(
            service_url="https://example.org/ogcapi",
            layer_name="buildings",
            protocol="ogcFeatures",
            table_name="places",
            engine=engine,
        )
        cmd = mock_run.call_args[0][0]
        assert "-a_srs" in cmd
        assert "EPSG:4326" in cmd

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


def _dbf(records: list[bytes], *, field: bytes = b"nom", width: int = 20) -> bytes:
    """Build a minimal .dbf holding one text field, for encoding-detection tests."""
    header_length = 32 + 32 + 1
    header = struct.pack("<B3BIHH20x", 3, 125, 1, 1, len(records), header_length, width + 1)
    header += field.ljust(11, b"\x00") + b"C" + b"\x00" * 4 + bytes([width]) + b"\x00" * 14
    header += b"\x0d"
    body = b"".join(b" " + r.ljust(width)[:width] for r in records) + b"\x1a"
    return header + body


_LATIN1_RECORDS = ["Café".encode("cp1252"), "Forêt".encode("cp1252")]


class TestShapefileEncodingDetection:
    """GDAL honours .cpg natively and assumes UTF-8 otherwise.

    Only the no-.cpg, non-UTF-8 case needs SHAPE_ENCODING: without it ogr2ogr
    aborts with "Non UTF-8 content found" and writes nothing.
    """

    def _shapefile(self, tmp_path: Path, *, cpg: str | None, dbf: bytes) -> str:
        (tmp_path / "z.shp").write_bytes(b"\x00")
        (tmp_path / "z.dbf").write_bytes(dbf)
        if cpg is not None:
            (tmp_path / "z.cpg").write_text(cpg)
        return str(tmp_path / "z.shp")

    def test_cpg_present_defers_to_gdal(self, tmp_path: Path) -> None:
        path = self._shapefile(tmp_path, cpg="ISO-8859-1", dbf=_dbf(_LATIN1_RECORDS))
        assert _detect_shapefile_encoding(path) is None

    def test_missing_cpg_with_latin_text_detects_cp1252(self, tmp_path: Path) -> None:
        path = self._shapefile(tmp_path, cpg=None, dbf=_dbf(_LATIN1_RECORDS))
        assert _detect_shapefile_encoding(path) == "CP1252"

    def test_ascii_content_defers_to_gdal(self, tmp_path: Path) -> None:
        # ASCII is valid UTF-8; overriding would be pointless.
        path = self._shapefile(tmp_path, cpg=None, dbf=_dbf([b"Paris", b"Lyon"]))
        assert _detect_shapefile_encoding(path) is None

    def test_non_shapefile_is_ignored(self, tmp_path: Path) -> None:
        plain = tmp_path / "data.geojson"
        plain.write_text('{"type":"FeatureCollection","features":[]}')
        assert _detect_shapefile_encoding(str(plain)) is None

    def test_zipped_shapefile_without_cpg_is_detected(self, tmp_path: Path) -> None:
        archive = tmp_path / "z.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("z.shp", b"\x00")
            zf.writestr("z.dbf", _dbf(_LATIN1_RECORDS))
        assert _detect_shapefile_encoding(str(archive)) == "CP1252"

    def test_zipped_shapefile_with_cpg_defers_to_gdal(self, tmp_path: Path) -> None:
        archive = tmp_path / "z.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("z.shp", b"\x00")
            zf.writestr("z.dbf", _dbf(_LATIN1_RECORDS))
            zf.writestr("z.cpg", "ISO-8859-1")
        assert _detect_shapefile_encoding(str(archive)) is None

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_shape_encoding_is_passed_to_ogr2ogr(
        self, mock_run: MagicMock, engine: Engine, tmp_path: Path
    ) -> None:
        mock_run.return_value = _completed()
        path = self._shapefile(tmp_path, cpg=None, dbf=_dbf(_LATIN1_RECORDS))

        ingest_file_with_ogr2ogr(path, "places", engine, schema="staging")

        cmd = mock_run.call_args[0][0]
        assert "SHAPE_ENCODING" in cmd
        assert "CP1252" in cmd

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_no_shape_encoding_when_cpg_present(
        self, mock_run: MagicMock, engine: Engine, tmp_path: Path
    ) -> None:
        mock_run.return_value = _completed()
        path = self._shapefile(tmp_path, cpg="UTF-8", dbf=_dbf(_LATIN1_RECORDS))

        ingest_file_with_ogr2ogr(path, "places", engine, schema="staging")

        assert "SHAPE_ENCODING" not in mock_run.call_args[0][0]


class TestOgrErrorDetection:
    """ogr2ogr exits 0 even when it aborts a layer, so stderr must be inspected."""

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_error_in_stderr_raises_despite_exit_zero(
        self, mock_run: MagicMock, engine: Engine
    ) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["ogr2ogr"],
            returncode=0,
            stdout="",
            stderr="ERROR 1: Non UTF-8 content found when writing feature -1\n",
        )
        with pytest.raises(Exception, match="Non UTF-8 content"):
            ingest_file_with_ogr2ogr("/tmp/data.geojson", "places", engine)

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_warnings_do_not_raise(self, mock_run: MagicMock, engine: Engine) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["ogr2ogr"], returncode=0, stdout="", stderr="Warning 6: Normalized/laundered\n"
        )
        ingest_file_with_ogr2ogr("/tmp/data.geojson", "places", engine)

    @patch("data_manipulation.ingestion.subprocess.run")
    def test_error_word_in_a_path_does_not_raise(self, mock_run: MagicMock, engine: Engine) -> None:
        # Anchored regex: only real "ERROR <n>:" lines count.
        mock_run.return_value = subprocess.CompletedProcess(
            args=["ogr2ogr"], returncode=0, stdout="", stderr="reading /data/error_log/x.shp\n"
        )
        ingest_file_with_ogr2ogr("/tmp/data.geojson", "places", engine)
