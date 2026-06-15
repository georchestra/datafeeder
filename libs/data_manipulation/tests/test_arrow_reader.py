"""Tests for the Arrow-native streaming readers (no DB required)."""

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from geoalchemy2 import Geometry
from geopandas import GeoDataFrame
from pyproj import CRS
from shapely.geometry import Point
from sqlalchemy import Column, DateTime, Integer, MetaData, Numeric, String, Table, Uuid

from data_manipulation.arrow_reader import (
    GeoMeta,
    _sqla_to_arrow,  # pyright: ignore[reportPrivateUsage]
    open_file,
    srid_from_crs,
)


class TestSridFromCrs:
    @pytest.mark.parametrize(
        "crs, expected",
        [
            ("EPSG:4326", 4326),
            ("EPSG4326", 4326),
            ("OGC:CRS84", 4326),
            (None, 0),
            ("garbage", 0),
            (2154, 2154),
        ],
    )
    def test_table_driven(self, crs: object, expected: int) -> None:
        assert srid_from_crs(crs) == expected

    def test_projjson_dict(self) -> None:
        projjson = CRS.from_epsg(2154).to_json_dict()
        assert srid_from_crs(projjson) == 2154


class TestOpenFile:
    def test_geojson_via_open_file(self, tmp_path: Path) -> None:
        gdf = GeoDataFrame(
            {"id": list(range(750))},
            geometry=[Point(i, i + 1) for i in range(750)],
            crs="EPSG:4326",
        )
        path = tmp_path / "data.geojson"
        gdf.to_file(path, driver="GeoJSON")

        with open_file(str(path), batch_rows=300) as src:
            assert src.geo is not None
            assert src.geo.srid == 4326
            assert src.geo.column in src.reader.schema.names
            total = sum(batch.num_rows for batch in src.reader)
        assert total == 750

    def test_plain_parquet_has_no_geo(self, tmp_path: Path) -> None:
        path = tmp_path / "tab.parquet"
        table = pa.table({"a": list(range(2500)), "b": [f"x{i}" for i in range(2500)]})
        pq.write_table(table, path)

        with open_file(str(path), batch_rows=1000) as src:
            assert src.geo is None
            total = sum(batch.num_rows for batch in src.reader)
        assert total == 2500

    def test_geoparquet_has_geo_4326(self, tmp_path: Path) -> None:
        gdf = GeoDataFrame(
            {"name": [f"p{i}" for i in range(1500)]},
            geometry=[Point(i, i) for i in range(1500)],
            crs="EPSG:4326",
        )
        path = tmp_path / "geo.parquet"
        gdf.to_parquet(path)

        with open_file(str(path), batch_rows=600) as src:
            assert src.geo is not None
            assert src.geo.srid == 4326
            total = sum(batch.num_rows for batch in src.reader)
        assert total == 1500

    def test_tabular_csv_via_ogr_has_no_geo(self, tmp_path: Path) -> None:
        path = tmp_path / "tab.csv"
        path.write_text("id,name\n1,alpha\n2,beta\n3,gamma\n")

        with open_file(str(path)) as src:
            assert src.geo is None
            total = sum(batch.num_rows for batch in src.reader)
        assert total == 3


class TestSqlaToArrow:
    def test_type_mapping_and_geometry(self) -> None:
        metadata = MetaData(schema="public")
        table = Table(
            "src",
            metadata,
            Column("id", Integer),
            Column("amount", Numeric(10, 2)),
            Column("label", String),
            Column("created", DateTime),
            Column("token", Uuid),
            Column("geom", Geometry(geometry_type="POINT", srid=2154)),
        )

        select_stmt, schema, geo = _sqla_to_arrow(table)
        compiled = str(select_stmt.compile(compile_kwargs={"literal_binds": True}))

        assert "ST_AsBinary" in compiled
        assert "CAST" in compiled.upper()

        fields = {f.name: f.type for f in schema}
        assert fields["id"] == pa.int64()
        assert fields["amount"] == pa.decimal128(10, 2)
        assert fields["label"] == pa.string()
        assert fields["created"] == pa.timestamp("us")
        assert fields["token"] == pa.string()
        assert fields["geom"] == pa.binary()

        assert geo == GeoMeta("geom", 2154)
