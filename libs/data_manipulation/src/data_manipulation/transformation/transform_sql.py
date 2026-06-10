"""SQL-only transformation path: staging → final table.

The Airflow process DAG transforms the staging table into the final table.
Historically this loaded everything into pandas, applied rename / cast /
projection in Python, and wrote it back. For anything beyond a small table
that double-trip dominates wall-clock and memory.

This module expresses the same transformations as one PostgreSQL statement
(`CREATE TABLE final AS SELECT … FROM staging`), so the dataset never enters
Python on the ELT path. The backend preview path (`read_and_transform_data`
with `limit=10`) keeps the existing Python implementation — same semantics,
guaranteed because filtering is already SQL-level via `build_sql_column_ops`.
"""

import logging
import re

from sqlalchemy import (
    MetaData,
    Table,
    bindparam,
    column,
    literal_column,
    select,
    text,
)
from sqlalchemy.engine import Engine

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN
from data_manipulation.models import CastType, ColumnConfig, IntegrityTransformation
from data_manipulation.transformation.filter_sql import build_sql_column_ops
from data_manipulation.validators import validate_schema_name, validate_table_name

logger = logging.getLogger(__name__)

# Boolean-text mapping mirrored from _parse_bool_from_strings (transform_columns.py)
# to keep preview/process parity (see CLAUDE.md backend.md: explicit mapper, no astype(bool)).
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
    preview and process produce identical results.
    """
    quoted = f'"{col_name}"'
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


def _build_select_expressions(
    columns: list[ColumnConfig],
    geom_expr: str | None,
) -> list[str]:
    """Return the SELECT list as raw SQL fragments (one entry per output column)."""
    parts: list[str] = []
    for cfg in columns:
        if cfg.excluded:
            continue
        effective = cfg.new_name or cfg.original_name
        if cfg.cast_type is not None:
            expr = _cast_expr(cfg.original_name, cfg.cast_type)
        else:
            expr = f'"{cfg.original_name}"'
        parts.append(f'{expr} AS "{effective}"')
    if geom_expr is not None:
        parts.append(f'{geom_expr} AS "{DEFAULT_GEOMETRY_COLUMN}"')
    return parts


def _build_geom_expression(
    staging_table: Table,
    config: IntegrityTransformation,
) -> str | None:
    """Build the SQL expression for the geometry column, or None for tabular data.

    Three cases mirror the Python apply_transformations logic:
      1. force_projection.x_column + force_projection.y_column → ST_MakePoint(x, y)
      2. staging has a 'geom' column + force_projection.type set → ST_Transform(geom)
      3. staging has a 'geom' column, no reprojection → pass through
    """
    fp = config.force_projection
    has_staging_geom = DEFAULT_GEOMETRY_COLUMN in staging_table.c

    if fp is not None and fp.x_column and fp.y_column:
        srid = _parse_srid(fp.type)
        x_expr = f'"{fp.x_column}"::double precision'
        y_expr = f'"{fp.y_column}"::double precision'
        point_expr = f"ST_SetSRID(ST_MakePoint({x_expr}, {y_expr}), {srid})"
        return point_expr

    if has_staging_geom:
        if fp is not None and fp.type:
            dst_srid = _parse_srid(fp.type)
            if dst_srid:
                return f'ST_Transform("{DEFAULT_GEOMETRY_COLUMN}", {dst_srid})'
        return f'"{DEFAULT_GEOMETRY_COLUMN}"'

    return None


def _build_where_sql(
    columns: list[ColumnConfig],
    staging_table: Table,
    engine: Engine,
) -> tuple[str, dict[str, object]]:
    """Compile WHERE clauses from build_sql_column_ops into a SQL string + bind params.

    Compiling via SQLAlchemy keeps user filter values as bound parameters
    (no SQL injection) while still emitting raw SQL we can splice into the
    surrounding `CREATE TABLE … AS SELECT` text.
    """
    _, where_clauses = build_sql_column_ops(columns, staging_table)
    if not where_clauses:
        return "", {}

    # Use a select() to compile the WHERE; SQLAlchemy 2.x renders bound params.
    stmt = select(literal_column("1")).where(*where_clauses)
    compiled = stmt.compile(
        bind=engine, compile_kwargs={"render_postcompile": True, "literal_binds": False}
    )
    sql = str(compiled)
    where_idx = sql.upper().rfind(" WHERE ")
    if where_idx == -1:
        return "", {}
    return sql[where_idx + len(" WHERE ") :], dict(compiled.params)


def transform_in_place_via_sql(
    staging_table_name: str,
    staging_schema: str,
    target_table_name: str,
    target_schema: str,
    engine: Engine,
    config: IntegrityTransformation | None,
    create_id: bool = True,
) -> int:
    """Run the staging → final transformation entirely in SQL.

    Returns the number of rows written to the final table.

    The dataset never leaves PostgreSQL: SELECT projects renamed/cast columns,
    PostGIS builds the geometry (X/Y or ST_Transform), the result is
    materialised into ``target_schema.target_table_name`` and a UUID primary
    key is added.
    """
    validate_table_name(staging_table_name)
    validate_schema_name(staging_schema)
    validate_table_name(target_table_name)
    validate_schema_name(target_schema)

    metadata = MetaData(schema=staging_schema)
    staging_table = Table(staging_table_name, metadata, autoload_with=engine)

    columns = (config.columns if config is not None else None) or []
    if columns:
        select_parts = _build_select_expressions(
            columns,
            _build_geom_expression(staging_table, config) if config is not None else None,
        )
        where_sql, where_params = _build_where_sql(columns, staging_table, engine)
    else:
        # No column config — pass every staging column through unchanged. Geometry,
        # if present, follows the same rules as the configured case.
        select_parts = [f'"{c.name}"' for c in staging_table.c if c.name != DEFAULT_GEOMETRY_COLUMN]
        geom_expr = _build_geom_expression(staging_table, config) if config is not None else None
        if geom_expr is None and DEFAULT_GEOMETRY_COLUMN in staging_table.c:
            geom_expr = f'"{DEFAULT_GEOMETRY_COLUMN}"'
        if geom_expr is not None:
            select_parts.append(f'{geom_expr} AS "{DEFAULT_GEOMETRY_COLUMN}"')
        where_sql, where_params = "", {}

    if not select_parts:
        raise ValueError(
            f"transform_in_place_via_sql: no columns selected from {staging_schema}.{staging_table_name}"
        )

    fq_target = f'"{target_schema}"."{target_table_name}"'
    fq_staging = f'"{staging_schema}"."{staging_table_name}"'
    select_clause = ", ".join(select_parts)
    where_clause = f" WHERE {where_sql}" if where_sql else ""
    create_sql = (
        f"DROP TABLE IF EXISTS {fq_target}; "
        f"CREATE TABLE {fq_target} AS SELECT {select_clause} FROM {fq_staging}{where_clause}"
    )

    logger.info(
        f"Running SQL transform: {staging_schema}.{staging_table_name} "
        f"→ {target_schema}.{target_table_name}"
    )
    logger.debug(f"SQL: {create_sql}")

    with engine.begin() as conn:
        # Drop is its own statement so AS-SELECT runs cleanly afterwards.
        conn.execute(text(f"DROP TABLE IF EXISTS {fq_target}"))
        bound = text(
            f"CREATE TABLE {fq_target} AS SELECT {select_clause} FROM {fq_staging}{where_clause}"
        )
        for k, v in where_params.items():
            bound = bound.bindparams(bindparam(k, value=v))
        conn.execute(bound)

        if create_id:
            conn.execute(
                text(
                    f"ALTER TABLE {fq_target} "
                    "ADD COLUMN id_datafeeder UUID DEFAULT gen_random_uuid() NOT NULL"
                )
            )
            conn.execute(text(f"ALTER TABLE {fq_target} ADD PRIMARY KEY (id_datafeeder)"))

        row_count = conn.execute(text(f"SELECT count(*) FROM {fq_target}")).scalar() or 0

    logger.info(f"SQL transform wrote {row_count} rows to {target_schema}.{target_table_name}")
    return int(row_count)


__all__ = ["transform_in_place_via_sql"]


_ = column  # keep import noise low — column() reserved for future extensions
