"""Arrow-native streaming readers for ingestion sources.

Every supported source (OGR-readable files, GeoParquet, PostGIS tables) is
exposed as an :class:`ArrowSource`: a :class:`pyarrow.RecordBatchReader` plus an
optional :class:`GeoMeta` describing the WKB geometry column. Geometry stays raw
WKB bytes end-to-end — no shapely roundtrip, no pandas materialisation — so peak
memory is bounded by ``batch_rows`` regardless of source size.

The table schema always comes from source metadata (OGR meta, GeoParquet
``geo`` metadata, or the reflected SQLAlchemy table), never inferred from the
first batch.
"""

import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chardet
import pyarrow as pa
import pyarrow.parquet as pq
import pyogrio.raw
from geoalchemy2 import Geometry
from pyproj import CRS
from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    Time,
    cast,
    func,
    literal_column,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Select
from sqlalchemy.types import Text as SAText

logger = logging.getLogger(__name__)

BATCH_ROWS = 50_000
_ENCODING_DETECT_BYTES = 256 * 1024

_EPSG_RE = re.compile(r"EPSG[:]*(\d+)")


@dataclass(frozen=True)
class GeoMeta:
    column: str  # name of the WKB binary column in the arrow stream
    srid: int  # 0 = unknown


@dataclass
class ArrowSource:
    reader: pa.RecordBatchReader
    geo: GeoMeta | None


def srid_from_crs(crs: object) -> int:
    """Best-effort SRID extraction. Returns 0 when the CRS is unknown.

    Handles pyogrio ``meta["crs"]`` strings (``"EPSG:4326"`` or WKT), GeoParquet
    PROJJSON dicts, ``"OGC:CRS84"`` and anything else pyproj can parse. Garbage
    falls through to 0.
    """
    if crs is None:
        return 0
    if isinstance(crs, str):
        m = _EPSG_RE.search(crs)
        if m:
            return int(m.group(1))
        # OGC:CRS84 is lon/lat WGS84; pyproj parses it but to_epsg() yields None.
        if "CRS84" in crs.upper():
            return 4326
    try:
        return CRS.from_user_input(crs).to_epsg() or 0
    except Exception:
        return 0


def detect_file_encoding(file_path: str) -> str:
    """Detect encoding for geospatial files.

    Args:
        file_path: Path to the file

    Returns:
        Detected encoding string
    """
    file_path_to_read = file_path
    path = Path(file_path)

    # GeoJSON must be UTF-8 according to RFC 7946
    if path.suffix.lower() in (".geojson", ".json"):
        return "utf-8"

    # Check for .cpg file (encoding file for shapefiles)
    if path.suffix.lower() == ".shp":
        cpg_file = path.with_suffix(".cpg")
        if cpg_file.exists():
            file_path_to_read = str(cpg_file)

    try:
        with open(file_path_to_read, "rb") as f:
            sample = f.read(_ENCODING_DETECT_BYTES)
        encoding = chardet.detect(sample)["encoding"]
    except Exception as e:
        logger.warning(f"Failed to detect encoding for {file_path_to_read}: {e}")
        encoding = None

    return encoding or "utf-8"


@contextmanager
def open_ogr(
    source: str,
    *,
    layer: str | None = None,
    encoding: str | None = None,
    batch_rows: int = BATCH_ROWS,
) -> Iterator[ArrowSource]:
    """Open any OGR-readable source (file or GDAL URL) as an Arrow stream."""
    with pyogrio.raw.open_arrow(
        source,
        layer=layer,
        encoding=encoding,
        batch_size=batch_rows,
        return_fids=False,
    ) as (meta, stream):
        # pyogrio 0.10+ yields an _ArrowStream exposing the C-stream interface;
        # newer versions may hand back a RecordBatchReader directly.
        reader = (
            stream
            if isinstance(stream, pa.RecordBatchReader)
            else pa.RecordBatchReader.from_stream(stream)
        )
        geom_name = meta.get("geometry_name") or "wkb_geometry"
        has_geom = bool(meta.get("geometry_type")) and geom_name in reader.schema.names
        geo = GeoMeta(geom_name, srid_from_crs(meta.get("crs"))) if has_geom else None
        yield ArrowSource(reader=reader, geo=geo)


def _parquet_geo(pf: pq.ParquetFile) -> tuple[str | None, object | None]:
    """Extract (primary geometry column, CRS) from GeoParquet ``geo`` metadata.

    GeoParquet < 1.0 sometimes omitted CRS — the spec default is OGC:CRS84
    (lon/lat, EPSG:4326-equivalent). Returns ``(None, None)`` for plain parquet.
    """
    md = pf.schema_arrow.metadata or {}
    raw = md.get(b"geo")
    if not raw:
        return None, None
    try:
        geo = json.loads(raw)
        primary = geo.get("primary_column", "geometry")
        col = geo.get("columns", {}).get(primary, {})
        crs = col.get("crs")
        return primary, "OGC:CRS84" if crs is None else crs
    except Exception as e:
        logger.warning(f"Failed to parse GeoParquet metadata: {e}")
        return None, None


@contextmanager
def open_parquet(path: str, *, batch_rows: int = BATCH_ROWS) -> Iterator[ArrowSource]:
    """Open a (Geo)Parquet file as an Arrow stream; geometry stays raw WKB."""
    pf = pq.ParquetFile(path)
    primary, crs = _parquet_geo(pf)
    reader = pa.RecordBatchReader.from_batches(
        pf.schema_arrow, pf.iter_batches(batch_size=batch_rows)
    )
    geo = (
        GeoMeta(primary, srid_from_crs(crs))
        if primary is not None and primary in reader.schema.names
        else None
    )
    yield ArrowSource(reader=reader, geo=geo)


@contextmanager
def open_file(
    path: str, *, encoding: str | None = None, batch_rows: int = BATCH_ROWS
) -> Iterator[ArrowSource]:
    """Open a local file as an Arrow stream, dispatching on the suffix."""
    suffix = Path(path).suffix.lower()
    if suffix in (".parquet", ".geoparquet"):
        with open_parquet(path, batch_rows=batch_rows) as src:
            yield src
    else:
        with open_ogr(path, encoding=encoding, batch_rows=batch_rows) as src:
            yield src


def _sqla_to_arrow(table: Table) -> tuple[Select[Any], pa.Schema, GeoMeta | None]:
    """Build (SELECT, arrow schema, geo) from a reflected SQLAlchemy table.

    Geometry columns are read as WKB via ``ST_AsBinary`` so they stay raw bytes;
    types pyarrow can't map directly (UUID, JSON, ARRAY...) are cast to text in
    the database so the Python-side arrays always build.
    """
    select_exprs: list[Any] = []
    fields: list[pa.Field] = []
    geo: GeoMeta | None = None

    for col in table.c:
        name = col.name
        col_type = col.type

        if isinstance(col_type, Geometry):
            select_exprs.append(
                func.ST_AsBinary(literal_column(f'"{name}"')).label(name)
            )
            fields.append(pa.field(name, pa.binary()))
            if geo is None or name == "geom":
                srid = col_type.srid if col_type.srid and col_type.srid > 0 else 0
                geo = GeoMeta(name, srid)
            continue

        arrow_type: pa.DataType
        if isinstance(col_type, Boolean):
            arrow_type = pa.bool_()
        elif isinstance(col_type, (Integer, BigInteger, SmallInteger)):
            arrow_type = pa.int64()
        elif isinstance(col_type, Float):
            arrow_type = pa.float64()
        elif isinstance(col_type, Numeric):
            if col_type.precision:
                arrow_type = pa.decimal128(col_type.precision, col_type.scale or 0)
            else:
                arrow_type = pa.float64()
        elif isinstance(col_type, (String, Text, Enum)):
            arrow_type = pa.string()
        elif isinstance(col_type, Date):
            arrow_type = pa.date32()
        elif isinstance(col_type, DateTime):
            arrow_type = pa.timestamp("us", tz="UTC" if col_type.timezone else None)
        elif isinstance(col_type, Time):
            arrow_type = pa.time64("us")
        elif isinstance(col_type, LargeBinary):
            arrow_type = pa.binary()
        else:
            # UUID, JSON, ARRAY, ... — convert in the DB so arrays always build.
            select_exprs.append(cast(col, SAText).label(name))
            fields.append(pa.field(name, pa.string()))
            continue

        select_exprs.append(col)
        fields.append(pa.field(name, arrow_type))

    return select(*select_exprs).select_from(table), pa.schema(fields), geo


@contextmanager
def open_postgis_table(
    table_name: str, schema: str, engine: Engine, *, batch_rows: int = BATCH_ROWS
) -> Iterator[ArrowSource]:
    """Open a PostGIS table as an Arrow stream (db→db ingestion source)."""
    metadata = MetaData(schema=schema)
    table = Table(table_name, metadata, autoload_with=engine)
    select_stmt, arrow_schema, geo = _sqla_to_arrow(table)

    conn = engine.connect().execution_options(stream_results=True, yield_per=batch_rows)
    try:
        result = conn.execute(select_stmt)

        def _gen() -> Iterator[pa.RecordBatch]:
            for partition in result.partitions(batch_rows):
                columns = list(zip(*partition)) if partition else [[] for _ in arrow_schema]
                arrays = [
                    pa.array(list(col_values), type=field.type)
                    for col_values, field in zip(columns, arrow_schema)
                ]
                yield pa.RecordBatch.from_arrays(arrays, schema=arrow_schema)

        yield ArrowSource(
            reader=pa.RecordBatchReader.from_batches(arrow_schema, _gen()),
            geo=geo,
        )
    finally:
        conn.close()
