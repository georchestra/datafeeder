"""SQL-native transformation pipeline: staging → final table.

Every transformation — column selection/exclusion, rename, type cast, filter,
projection and geometry construction — is expressed as parameterized SQL
(SQLAlchemy Core) and executed inside PostGIS. Data never leaves the database
except for the small bounded preview.

A single :func:`build_transformation_select` produces the canonical
transformation ``SELECT`` used by both:

* :func:`transform_staging_to_final` — ``CREATE TABLE <final> AS <select>``
  (the Airflow process path), and
* :func:`read_transformed_preview` — ``<select>`` + ``LIMIT`` with in-database
  geometry serialization (the backend preview path).

Building the query once guarantees preview and process apply identical
transformations.

Projection semantics for an existing geometry:

* ``force_projection.type`` reprojects coordinates via ``ST_Transform`` — except
  when the source SRID is 0 (unknown), where ``ST_SetSRID`` labels the SRID
  in place because there is no source CRS to reproject from.
* The map preview reprojects to EPSG:4326 for display, leaving SRID-0 geometry
  as-is (rendered in whatever coordinate space it already carries).
"""

import datetime
import json
import logging
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Column,
    ColumnElement,
    MetaData,
    Table,
    func,
    literal_column,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.sql import Select
from sqlalchemy.sql.expression import case

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN, POSTGIS_TABLE_NAME_MAX_LENGTH
from data_manipulation.models import CastType, IntegrityTransformation
from data_manipulation.transformation.filter_sql import build_filter_clause
from data_manipulation.validators import validate_schema_name, validate_table_name

logger = logging.getLogger(__name__)

DEFAULT_SRID = 4326

# Boolean-text mapping mirrored from the former pandas parser so text-encoded
# booleans cast identically on the preview and process paths.
_BOOL_TRUE_TOKENS = ("true", "1", "yes", "on", "t", "y")
_BOOL_FALSE_TOKENS = ("false", "0", "no", "off", "f", "n")

_EPSG_RE = re.compile(r"EPSG\s*:\s*(\d+)", re.IGNORECASE)


def _parse_srid(value: str | None) -> int:
    """Parse a CRS string like ``"EPSG:4326"`` into a numeric SRID. 0 if unknown."""
    if not value:
        return 0
    m = _EPSG_RE.search(value)
    if m:
        return int(m.group(1))
    if value.isdigit():
        return int(value)
    return 0


def _cast_expr(col_name: str, cast_type: CastType) -> str:
    """SQL expression that casts an existing column to the requested type.

    Bool-from-text mirrors the explicit token map used by the Python path so
    preview and process produce identical results. *col_name* is only ever a
    name verified present in ``table.c``, but the double-quote doubling keeps
    the identifier safe regardless.
    """
    quoted = '"' + col_name.replace('"', '""') + '"'
    if cast_type == CastType.BOOLEAN:
        true_list = ", ".join(f"'{t}'" for t in _BOOL_TRUE_TOKENS)
        false_list = ", ".join(f"'{t}'" for t in _BOOL_FALSE_TOKENS)
        return (
            f"CASE WHEN lower(trim({quoted}::text)) IN ({true_list}) THEN TRUE "
            f"WHEN lower(trim({quoted}::text)) IN ({false_list}) THEN FALSE "
            "ELSE NULL END"
        )
    if cast_type == CastType.NUMERIC:
        # Match pandas pd.to_numeric(errors="coerce") — invalid text → NULL.
        return (
            f"CASE WHEN {quoted}::text ~ "
            "'^-?[0-9]+(\\.[0-9]+)?([eE][-+]?[0-9]+)?$' "
            f"THEN {quoted}::text::double precision ELSE NULL END"
        )
    if cast_type == CastType.TEXT:
        return f"{quoted}::text"
    if cast_type == CastType.DATE:
        # Mirror pd.to_datetime(errors="coerce") leniency: accept ISO 8601 and
        # the most common day-first European separators (/, -, .). Anything
        # else falls through to NULL instead of raising (::timestamp does).
        iso_re = "'^[0-9]{4}-[0-9]{2}-[0-9]{2}'"
        dmy_re = r"'^[0-9]{1,2}[/.\-][0-9]{1,2}[/.\-][0-9]{4}'"
        return (
            "CASE "
            f"WHEN {quoted} IS NULL OR {quoted}::text = '' THEN NULL "
            f"WHEN {quoted}::text ~ {iso_re} THEN {quoted}::text::timestamp "
            f"WHEN {quoted}::text ~ {dmy_re} THEN "
            f"to_timestamp(regexp_replace({quoted}::text, '[.\\-]', '/', 'g'), 'FMDD/FMMM/YYYY') "
            "ELSE NULL END"
        )
    return quoted


def _geom_ref() -> ColumnElement[Any]:
    """Reference the staging geometry column as a plain (untyped) column.

    Using :func:`literal_column` instead of the reflected GeoAlchemy2 column
    avoids the automatic ``ST_AsEWKB(...)`` read-wrapping, so the geometry stays
    a native ``geometry`` value usable by ``CREATE TABLE AS`` and ``ST_*``.
    """
    return literal_column(f'"{DEFAULT_GEOMETRY_COLUMN}"')


def _force_srid_expr(geom: ColumnElement[Any], srid: int) -> ColumnElement[Any]:
    """Project *geom* to *srid*, labelling in place when the source SRID is 0.

    A SRID of 0 means the source CRS is unknown, so ``ST_Transform`` has nothing
    to reproject from; ``ST_SetSRID`` assigns the requested SRID instead.
    """
    return case(
        (func.ST_SRID(geom) == 0, func.ST_SetSRID(geom, srid)),
        else_=func.ST_Transform(geom, srid),
    )


def _display_4326_expr(geom: ColumnElement[Any]) -> ColumnElement[Any]:
    """Project *geom* to EPSG:4326 for the preview map, leaving SRID-0 as-is."""
    return case(
        (func.ST_SRID(geom) == 0, geom),
        else_=func.ST_Transform(geom, DEFAULT_SRID),
    )


@dataclass
class TransformationQuery:
    """Result of :func:`build_transformation_select`.

    Attributes:
        select: The canonical transformation ``SELECT`` against the staging table.
        geom_column: Name of the geometry output column (always
            :data:`DEFAULT_GEOMETRY_COLUMN`) when the result is geographic, else
            ``None``.
        property_columns: Ordered names of the non-geometry output columns.
    """

    select: Select[Any]
    geom_column: str | None
    property_columns: list[str] = field(default_factory=list)


def build_transformation_select(
    table: Table, config: IntegrityTransformation | None
) -> TransformationQuery:
    """Build the canonical transformation ``SELECT`` for a staging table.

    Applies, entirely in SQL:

    * column selection + exclusion (excluded columns are never selected),
    * rename (``new_name``) via column labels,
    * type cast (boolean/numeric/text/date) with invalid values coerced to NULL,
    * per-column ILIKE filters as bound-parameter ``WHERE`` clauses,
    * geometry handling:
        - X/Y columns → ``ST_SetSRID(ST_MakePoint(x, y), srid)``,
        - existing geom + forced projection → reproject (or label SRID when
          source SRID is 0),
        - existing geom, no/unparseable projection → passthrough.

    The geometry output is always named :data:`DEFAULT_GEOMETRY_COLUMN`; a
    ``new_name`` configured on the geometry column is ignored.

    Args:
        table: SQLAlchemy ``Table`` for the staging table.
        config: Transformation configuration. ``None`` selects all columns
            unchanged (passthrough), preserving any geometry column.

    Returns:
        A :class:`TransformationQuery`.
    """
    columns = config.columns if config is not None else None
    force = config.force_projection if config is not None else None

    geom_srid = _parse_srid(force.type) if force else 0
    x_col = force.x_column if force and force.x_column else None
    y_col = force.y_column if force and force.y_column else None
    build_point = bool(x_col and y_col)

    select_exprs: list[ColumnElement[Any]] = []
    where_clauses: list[ColumnElement[Any]] = []
    property_columns: list[str] = []
    geom_out: str | None = None

    def _emit_existing_geom() -> None:
        nonlocal geom_out
        geom = _geom_ref()
        expr = _force_srid_expr(geom, geom_srid) if geom_srid else geom
        select_exprs.append(expr.label(DEFAULT_GEOMETRY_COLUMN))
        geom_out = DEFAULT_GEOMETRY_COLUMN

    if columns:
        for col_config in columns:
            if col_config.excluded:
                continue
            name = col_config.original_name
            if name not in table.c:
                logger.warning("Column '%s' not found in table '%s', skipping", name, table.name)
                continue

            if name == DEFAULT_GEOMETRY_COLUMN:
                # Geometry is emitted separately and never renamed. When X/Y
                # columns build the point, the existing geom is discarded.
                if not build_point:
                    _emit_existing_geom()
                continue

            col: Column[Any] = table.c[name]
            if col_config.cast_type:
                expr: ColumnElement[Any] = literal_column(_cast_expr(name, col_config.cast_type))
            else:
                expr = col
            effective = col_config.new_name or col_config.original_name
            select_exprs.append(expr.label(effective))
            property_columns.append(effective)

            if col_config.filter is not None:
                where_clauses.append(build_filter_clause(table.c[name], col_config.filter))
    else:
        for col in table.c:
            if col.name == DEFAULT_GEOMETRY_COLUMN:
                if not build_point:
                    _emit_existing_geom()
                continue
            select_exprs.append(col)
            property_columns.append(col.name)

    if build_point and x_col is not None and y_col is not None:
        srid = geom_srid or DEFAULT_SRID
        x_expr = literal_column(_cast_expr(x_col, CastType.NUMERIC))
        y_expr = literal_column(_cast_expr(y_col, CastType.NUMERIC))
        point = func.ST_SetSRID(func.ST_MakePoint(x_expr, y_expr), srid)
        select_exprs.append(point.label(DEFAULT_GEOMETRY_COLUMN))
        geom_out = DEFAULT_GEOMETRY_COLUMN

    stmt = select(*select_exprs).select_from(table)
    if where_clauses:
        stmt = stmt.where(*where_clauses)

    return TransformationQuery(select=stmt, geom_column=geom_out, property_columns=property_columns)


# --------------------------------------------------------------------------- #
# Process path: staging -> final (CREATE TABLE AS)
# --------------------------------------------------------------------------- #


def transform_staging_to_final(
    staging_table: str,
    final_table: str,
    engine: Engine,
    config: IntegrityTransformation | None = None,
    *,
    staging_schema: str = "staging",
    final_schema: str = "data",
    create_id: bool = True,
) -> int:
    """Transform a staging table into a final table entirely in the database.

    Runs ``CREATE TABLE <final_schema>.<final_table> AS <transformation SELECT>``
    and optionally adds an ``id_datafeeder`` UUID primary key plus a GIST index
    on the geometry column. No data is loaded into Python memory.

    Args:
        staging_table: Source staging table name.
        final_table: Target final table name.
        engine: SQLAlchemy engine for the (single) PostGIS database.
        config: Transformation configuration (``None`` = passthrough copy).
        staging_schema: Schema of the staging table.
        final_schema: Schema of the final table.
        create_id: When True, add an ``id_datafeeder`` UUID primary key.

    Returns:
        Number of rows written to the final table.
    """
    validate_schema_name(staging_schema)
    validate_schema_name(final_schema)
    validate_table_name(staging_table)
    # The GIST index name budget (idx_<table>_geom) applies to the final table.
    validate_table_name(final_table, max_length=POSTGIS_TABLE_NAME_MAX_LENGTH)

    metadata = MetaData(schema=staging_schema)
    table = Table(staging_table, metadata, autoload_with=engine)

    tq = build_transformation_select(table, config)
    compiled = tq.select.compile(dialect=engine.dialect)

    with engine.begin() as conn:
        # Replace semantics: CREATE TABLE AS requires the target not to exist.
        conn.execute(text(f'DROP TABLE IF EXISTS "{final_schema}"."{final_table}"'))
        # exec_driver_sql passes the DBAPI-paramstyle SQL + params straight
        # through, keeping every filter value a bound parameter.
        conn.exec_driver_sql(
            f'CREATE TABLE "{final_schema}"."{final_table}" AS {compiled.string}',
            compiled.params,
        )

        if create_id:
            conn.execute(
                text(
                    f'ALTER TABLE "{final_schema}"."{final_table}" '
                    "ADD COLUMN id_datafeeder UUID DEFAULT gen_random_uuid() NOT NULL"
                )
            )
            conn.execute(
                text(
                    f'ALTER TABLE "{final_schema}"."{final_table}" ADD PRIMARY KEY (id_datafeeder)'
                )
            )

        if tq.geom_column:
            conn.execute(
                text(
                    f'CREATE INDEX "idx_{final_table}_geom" '
                    f'ON "{final_schema}"."{final_table}" USING GIST ("{tq.geom_column}")'
                )
            )

        row_count = (
            conn.execute(text(f'SELECT count(*) FROM "{final_schema}"."{final_table}"')).scalar()
            or 0
        )

    logger.info(
        "Transformed %s.%s -> %s.%s (%d rows)",
        staging_schema,
        staging_table,
        final_schema,
        final_table,
        row_count,
    )
    return int(row_count)


# --------------------------------------------------------------------------- #
# Preview path: staging -> bounded rows + GeoJSON
# --------------------------------------------------------------------------- #


@dataclass
class PreviewResult:
    """Bounded, JSON-serializable preview of a transformed staging table.

    Attributes:
        rows: Tabular rows (geometry rendered as WKT under ``geom``).
        geojson: A GeoJSON ``FeatureCollection`` (EPSG:4326) or ``None``.
        is_geographic: Whether the transformed result has a geometry column.
    """

    rows: list[dict[str, Any]]
    geojson: dict[str, Any] | None
    is_geographic: bool


def _json_safe(value: Any) -> Any:
    """Convert DB-native scalar types to JSON-serializable equivalents."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return value


def read_transformed_preview(
    staging_table: str,
    engine: Engine,
    config: IntegrityTransformation | None = None,
    *,
    schema: str = "staging",
    limit: int | None = 10,
) -> PreviewResult:
    """Read a bounded, transformed preview of a staging table.

    Builds the same transformation ``SELECT`` as the process path, applies a
    ``LIMIT`` and serializes geometry in the database: WKT for the tabular rows
    (``geom``) and GeoJSON reprojected to EPSG:4326 for map display. No
    geopandas/pandas involved.

    Args:
        staging_table: Staging table name.
        engine: SQLAlchemy engine.
        config: Transformation configuration (``None`` = passthrough).
        schema: Staging schema.
        limit: Maximum number of rows (``None`` = no limit).

    Returns:
        A :class:`PreviewResult`.
    """
    validate_table_name(staging_table)
    validate_schema_name(schema)

    metadata = MetaData(schema=schema)
    table = Table(staging_table, metadata, autoload_with=engine)

    tq = build_transformation_select(table, config)
    core = tq.select.subquery()

    geojson_label = "__geojson__"
    geom_column = tq.geom_column
    has_geom = geom_column is not None

    select_cols: list[ColumnElement[Any]] = []
    for col in core.c:
        if col.name == geom_column:
            select_cols.append(func.ST_AsText(col).label(DEFAULT_GEOMETRY_COLUMN))
        else:
            select_cols.append(col)
    if geom_column is not None:
        geom_col = core.c[geom_column]
        select_cols.append(func.ST_AsGeoJSON(_display_4326_expr(geom_col)).label(geojson_label))

    stmt = select(*select_cols)
    if limit is not None and limit > 0:
        stmt = stmt.limit(limit)

    rows: list[dict[str, Any]] = []
    features: list[dict[str, Any]] = []

    with engine.connect() as conn:
        result = conn.execute(stmt)
        for mapping in result.mappings():
            record = dict(mapping)
            geometry_geojson = record.pop(geojson_label, None) if has_geom else None

            row = {key: _json_safe(val) for key, val in record.items()}
            rows.append(row)

            if has_geom and geometry_geojson:
                properties = {
                    key: val for key, val in row.items() if key != DEFAULT_GEOMETRY_COLUMN
                }
                features.append(
                    {
                        "type": "Feature",
                        "geometry": json.loads(geometry_geojson),
                        "properties": properties,
                    }
                )

    geojson = {"type": "FeatureCollection", "features": features} if has_geom and features else None
    return PreviewResult(rows=rows, geojson=geojson, is_geographic=has_geom)


# --------------------------------------------------------------------------- #
# CRS detection
# --------------------------------------------------------------------------- #


def detect_table_srid(staging_table: str, engine: Engine, schema: str | None = None) -> str | None:
    """Return the CRS (``EPSG:NNNN``) of a staging table's geometry, if any.

    Reads ``ST_SRID`` from the first geometry row. Returns ``None`` when the
    table has no geometry column or no detectable SRID.
    """
    validate_table_name(staging_table)
    if schema:
        validate_schema_name(schema)

    try:
        metadata = MetaData(schema=schema)
        table = Table(staging_table, metadata, autoload_with=engine)
    except Exception as exc:
        logger.warning("Could not reflect table for SRID detection: %s", exc)
        return None

    if DEFAULT_GEOMETRY_COLUMN not in table.c:
        return None

    try:
        with engine.connect() as conn:
            srid = conn.execute(
                select(func.ST_SRID(_geom_ref())).select_from(table).limit(1)
            ).scalar()
    except Exception as exc:
        logger.warning("Could not detect original projection: %s", exc)
        return None

    if srid:
        return f"EPSG:{srid}"
    return None
