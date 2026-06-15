"""ADBC bulk writer: Arrow stream → PostGIS table.

The geometry column arrives as raw WKB bytes from the readers in
:mod:`data_manipulation.arrow_reader`. We bulk-load every batch with
``adbc_ingest`` (COPY BINARY under the hood) into a binary ``geom`` column, then
fix it up to a native PostGIS ``geometry`` with a single ``ALTER TABLE`` plus a
GIST index — all inside one transaction, so a mid-stream failure rolls the table
replacement back and the old table survives.
"""

import json
import logging
from collections.abc import Iterator
from typing import Any

import pyarrow as pa
import pyarrow.compute as pc
from adbc_driver_postgresql import dbapi
from sqlalchemy.engine import Engine

from data_manipulation.arrow_reader import ArrowSource, GeoMeta
from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN, POSTGIS_TABLE_NAME_MAX_LENGTH
from data_manipulation.validators import validate_schema_name, validate_table_name

logger = logging.getLogger(__name__)


def adbc_uri_from_engine(engine: Engine) -> str:
    """Render a plain ``postgresql://`` URI from a SQLAlchemy engine URL.

    Works for ``postgresql+psycopg2`` and ``postgresql+psycopg`` and preserves
    query parameters. Never log the result — it carries the password.
    """
    return engine.url.set(drivername="postgresql").render_as_string(hide_password=False)


def normalize_schema(schema: pa.Schema, geo: GeoMeta | None) -> pa.Schema:
    """Compute the target Arrow schema after the geometry/type normalisation rules."""
    fields: list[pa.Field] = []
    drop_stray_geom = False
    rename_from: str | None = None

    if geo is not None and geo.column != DEFAULT_GEOMETRY_COLUMN:
        if DEFAULT_GEOMETRY_COLUMN in schema.names:
            drop_stray_geom = True
            logger.warning(
                "Source has both '%s' and a '%s' column; dropping the stray '%s'.",
                geo.column,
                DEFAULT_GEOMETRY_COLUMN,
                DEFAULT_GEOMETRY_COLUMN,
            )
        rename_from = geo.column
    elif geo is None and DEFAULT_GEOMETRY_COLUMN in schema.names:
        drop_stray_geom = True
        logger.warning(
            "Non-geographic source has a '%s' column (reserved for PostGIS); dropping it.",
            DEFAULT_GEOMETRY_COLUMN,
        )

    for field in schema:
        if drop_stray_geom and field.name == DEFAULT_GEOMETRY_COLUMN:
            continue
        name = DEFAULT_GEOMETRY_COLUMN if field.name == rename_from else field.name
        fields.append(pa.field(name, _normalized_type(field.type)))

    return pa.schema(fields)


def _normalized_type(field_type: pa.DataType) -> pa.DataType:
    """Target Arrow type for a field after normalisation."""
    if pa.types.is_dictionary(field_type):
        return field_type.value_type
    if pa.types.is_null(field_type):
        return pa.string()
    if (
        pa.types.is_list(field_type)
        or pa.types.is_large_list(field_type)
        or pa.types.is_struct(field_type)
        or pa.types.is_map(field_type)
    ):
        return pa.string()
    return field_type


def _normalize_batch(batch: pa.RecordBatch, target_schema: pa.Schema) -> pa.RecordBatch:
    """Apply the geometry/type rules to a single batch, matching ``target_schema``."""
    arrays: list[pa.Array] = []
    for target_field in target_schema:
        # The source field keeps its original name; only the geometry column is
        # renamed, and it is the only field whose name may differ. Match by
        # position via the (already normalised) target order.
        src = batch.column(_source_index(batch.schema, target_field, target_schema))
        arrays.append(_normalize_array(src, target_field.type))
    return pa.RecordBatch.from_arrays(arrays, schema=target_schema)


def _source_index(
    src_schema: pa.Schema, target_field: pa.Field, target_schema: pa.Schema
) -> int:
    """Locate the source column feeding ``target_field`` in the normalised schema.

    Names are unchanged except the renamed geometry column, which is the single
    field present in the target but absent (under that name) from the source.
    """
    if target_field.name in src_schema.names:
        return src_schema.get_field_index(target_field.name)
    # The renamed geometry column: the one source name not kept in the target.
    target_names = set(target_schema.names)
    for i, name in enumerate(src_schema.names):
        if name not in target_names:
            return i
    raise KeyError(f"No source column for target field {target_field.name!r}")


def _normalize_array(array: pa.Array, target_type: pa.DataType) -> pa.Array:
    """Coerce a single column to ``target_type`` per the normalisation rules."""
    src_type = array.type
    if pa.types.is_dictionary(src_type):
        return pc.cast(array.dictionary_decode(), target_type)
    if pa.types.is_null(src_type):
        return pc.cast(array, target_type)
    if (
        pa.types.is_list(src_type)
        or pa.types.is_large_list(src_type)
        or pa.types.is_struct(src_type)
        or pa.types.is_map(src_type)
    ):
        return pa.array(
            [None if v is None else json.dumps(v) for v in array.to_pylist()],
            type=target_type,
        )
    return array


def _normalizing_reader(
    reader: pa.RecordBatchReader, geo: GeoMeta | None
) -> pa.RecordBatchReader:
    """Wrap a reader so every batch is normalised to the target schema lazily."""
    target_schema = normalize_schema(reader.schema, geo)

    def _gen() -> Iterator[pa.RecordBatch]:
        for batch in reader:
            yield _normalize_batch(batch, target_schema)

    return pa.RecordBatchReader.from_batches(target_schema, _gen())


def geometry_fixup_ddl(schema: str, table: str, srid: int) -> list[str]:
    """DDL converting the binary ``geom`` column to native ``geometry`` + GIST index."""
    fq = f'"{schema}"."{table}"'
    geom = f'"{DEFAULT_GEOMETRY_COLUMN}"'
    if srid > 0:
        alter = (
            f"ALTER TABLE {fq} ALTER COLUMN {geom} TYPE geometry(Geometry, {srid}) "
            f"USING ST_GeomFromWKB({geom}, {srid})"
        )
    else:
        alter = (
            f"ALTER TABLE {fq} ALTER COLUMN {geom} TYPE geometry "
            f"USING ST_GeomFromWKB({geom})"
        )
    index = (
        f'CREATE INDEX "idx_{table}_{DEFAULT_GEOMETRY_COLUMN}" '
        f"ON {fq} USING GIST ({geom})"
    )
    return [alter, index]


def write_arrow_to_postgis(
    source: ArrowSource,
    table_name: str,
    engine: Engine,
    schema: str = "public",
) -> int:
    """Bulk-load an Arrow source into ``schema.table_name`` via ADBC.

    Replaces the target table (drop + recreate from the source schema) inside a
    single transaction, fixes up the geometry column, and returns the inserted
    row count. An empty source still creates the (empty) table.
    """
    validate_table_name(table_name, max_length=POSTGIS_TABLE_NAME_MAX_LENGTH)
    validate_schema_name(schema)

    reader = _normalizing_reader(source.reader, source.geo)
    uri = adbc_uri_from_engine(engine)

    with dbapi.connect(uri) as conn:
        with conn.cursor() as cur:
            # adbc_ingest reports rows affected, but some driver/mode combinations
            # return -1 or None; fall back to a COUNT(*) in that case.
            ingested: Any = cur.adbc_ingest(
                table_name, reader, mode="replace", db_schema_name=schema
            )
            if source.geo is not None:
                for ddl in geometry_fixup_ddl(schema, table_name, source.geo.srid):
                    cur.execute(ddl)
            if ingested is None or ingested < 0:
                cur.execute(f'SELECT count(*) FROM "{schema}"."{table_name}"')
                row = cur.fetchone()
                rows = int(row[0]) if row is not None else 0
            else:
                rows = int(ingested)
        conn.commit()

    logger.info("Successfully inserted %d rows into %s.%s", rows, schema, table_name)
    return rows
