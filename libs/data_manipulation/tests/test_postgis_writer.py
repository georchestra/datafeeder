"""Tests for the ADBC PostGIS writer (no DB required, ADBC connection mocked)."""

from unittest.mock import MagicMock, patch

import pyarrow as pa
import pytest
from sqlalchemy.engine import Engine, make_url

from data_manipulation.arrow_reader import ArrowSource, GeoMeta
from data_manipulation.postgis_writer import (
    _normalize_batch,  # pyright: ignore[reportPrivateUsage]
    adbc_uri_from_engine,
    geometry_fixup_ddl,
    normalize_schema,
    write_arrow_to_postgis,
)


def _engine_with_url(url: str) -> MagicMock:
    """Mock Engine carrying a real SQLAlchemy URL.

    Avoids ``create_engine`` so the test does not need the psycopg DBAPI (a
    backend-only dependency) installed in the lib's environment.
    """
    engine = MagicMock(spec=Engine)
    engine.url = make_url(url)
    return engine


class TestAdbcUriFromEngine:
    def test_psycopg2_strips_driver_keeps_password(self) -> None:
        uri = adbc_uri_from_engine(_engine_with_url("postgresql+psycopg2://u:p@h:5432/db"))
        assert uri == "postgresql://u:p@h:5432/db"

    def test_psycopg_strips_driver_keeps_password(self) -> None:
        uri = adbc_uri_from_engine(_engine_with_url("postgresql+psycopg://u:p@h:5432/db"))
        assert uri == "postgresql://u:p@h:5432/db"


class TestNormalizeSchema:
    def test_renames_wkb_geometry_to_geom(self) -> None:
        schema = pa.schema([("id", pa.int64()), ("wkb_geometry", pa.binary())])
        out = normalize_schema(schema, GeoMeta("wkb_geometry", 4326))
        assert out.names == ["id", "geom"]

    def test_stray_geom_dropped_when_renaming(self) -> None:
        schema = pa.schema(
            [("id", pa.int64()), ("wkb_geometry", pa.binary()), ("geom", pa.string())]
        )
        out = normalize_schema(schema, GeoMeta("wkb_geometry", 4326))
        assert out.names == ["id", "geom"]
        assert out.field("geom").type == pa.binary()

    def test_stray_geom_dropped_when_non_geographic(self) -> None:
        schema = pa.schema([("id", pa.int64()), ("geom", pa.string())])
        out = normalize_schema(schema, None)
        assert out.names == ["id"]

    def test_list_column_becomes_string(self) -> None:
        schema = pa.schema([("tags", pa.list_(pa.int64()))])
        out = normalize_schema(schema, None)
        assert out.field("tags").type == pa.string()

    def test_dictionary_decoded(self) -> None:
        schema = pa.schema([("cat", pa.dictionary(pa.int32(), pa.string()))])
        out = normalize_schema(schema, None)
        assert out.field("cat").type == pa.string()


class TestNormalizeBatch:
    def test_rename_and_list_to_json(self) -> None:
        batch = pa.record_batch(
            {
                "id": pa.array([1, 2]),
                "wkb_geometry": pa.array([b"\x01", b"\x02"], type=pa.binary()),
                "tags": pa.array([[1, 2], None], type=pa.list_(pa.int64())),
            }
        )
        target = normalize_schema(batch.schema, GeoMeta("wkb_geometry", 4326))
        out = _normalize_batch(batch, target)

        assert out.schema.names == ["id", "geom", "tags"]
        assert out.column("geom").to_pylist() == [b"\x01", b"\x02"]
        assert out.column("tags").to_pylist() == ["[1, 2]", None]

    def test_dictionary_decoded_values(self) -> None:
        batch = pa.record_batch(
            {"cat": pa.array(["a", "b", "a"]).dictionary_encode()}
        )
        target = normalize_schema(batch.schema, None)
        out = _normalize_batch(batch, target)
        assert out.column("cat").to_pylist() == ["a", "b", "a"]


class TestGeometryFixupDdl:
    def test_srid_present(self) -> None:
        ddl = geometry_fixup_ddl("staging", "communes", 2154)
        assert ddl == [
            'ALTER TABLE "staging"."communes" ALTER COLUMN "geom" '
            "TYPE geometry(Geometry, 2154) USING ST_GeomFromWKB(\"geom\", 2154)",
            'CREATE INDEX "idx_communes_geom" ON "staging"."communes" USING GIST ("geom")',
        ]

    def test_srid_zero(self) -> None:
        ddl = geometry_fixup_ddl("staging", "communes", 0)
        assert ddl == [
            'ALTER TABLE "staging"."communes" ALTER COLUMN "geom" '
            'TYPE geometry USING ST_GeomFromWKB("geom")',
            'CREATE INDEX "idx_communes_geom" ON "staging"."communes" USING GIST ("geom")',
        ]


class TestWriteArrowToPostgis:
    @pytest.fixture
    def engine(self) -> MagicMock:
        return _engine_with_url("postgresql+psycopg://u:p@h:5432/db")

    @staticmethod
    def _source(geo: GeoMeta | None, batches: list[pa.RecordBatch]) -> ArrowSource:
        if batches:
            schema = batches[0].schema
        else:
            schema = pa.schema([("id", pa.int64()), ("geom", pa.binary())]) if geo else pa.schema(
                [("id", pa.int64())]
            )
        reader = pa.RecordBatchReader.from_batches(schema, iter(batches))
        return ArrowSource(reader=reader, geo=geo)

    @staticmethod
    def _connect_mock() -> tuple[MagicMock, MagicMock, MagicMock]:
        cur = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value = cur
        connect = MagicMock()
        connect.return_value.__enter__.return_value = conn
        return connect, conn, cur

    @patch("data_manipulation.postgis_writer.dbapi.connect")
    def test_ingest_replace_with_ddl_and_commit(
        self, mock_connect: MagicMock, engine: MagicMock
    ) -> None:
        connect, conn, cur = self._connect_mock()
        mock_connect.side_effect = connect
        cur.adbc_ingest.return_value = 3

        batch = pa.record_batch(
            {
                "id": pa.array([1, 2, 3]),
                "geom": pa.array([b"\x01", b"\x02", b"\x03"], type=pa.binary()),
            }
        )
        source = self._source(GeoMeta("geom", 2154), [batch])

        rows = write_arrow_to_postgis(source, "communes", engine, schema="staging")

        assert rows == 3
        ingest_call = cur.adbc_ingest.call_args
        assert ingest_call.args[0] == "communes"
        assert ingest_call.kwargs["mode"] == "replace"
        assert ingest_call.kwargs["db_schema_name"] == "staging"
        # DDL executed in order after ingest.
        executed = [c.args[0] for c in cur.execute.call_args_list]
        assert executed == geometry_fixup_ddl("staging", "communes", 2154)
        conn.commit.assert_called_once()

    @patch("data_manipulation.postgis_writer.dbapi.connect")
    def test_no_commit_when_ingest_raises(
        self, mock_connect: MagicMock, engine: MagicMock
    ) -> None:
        connect, conn, cur = self._connect_mock()
        mock_connect.side_effect = connect
        cur.adbc_ingest.side_effect = RuntimeError("boom")

        batch = pa.record_batch({"id": pa.array([1])})
        source = self._source(None, [batch])

        with pytest.raises(RuntimeError, match="boom"):
            write_arrow_to_postgis(source, "tbl", engine, schema="public")

        conn.commit.assert_not_called()

    @patch("data_manipulation.postgis_writer.dbapi.connect")
    def test_empty_reader_still_ingests(
        self, mock_connect: MagicMock, engine: MagicMock
    ) -> None:
        connect, conn, cur = self._connect_mock()
        mock_connect.side_effect = connect
        cur.adbc_ingest.return_value = 0

        source = self._source(None, [])
        rows = write_arrow_to_postgis(source, "tbl", engine, schema="public")

        assert rows == 0
        cur.adbc_ingest.assert_called_once()
        conn.commit.assert_called_once()
