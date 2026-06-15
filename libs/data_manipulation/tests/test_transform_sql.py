"""Tests for the SQL-native transform path (no PG required, mocked engine)."""

import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine

from data_manipulation.models import (
    CastType,
    ColumnConfig,
    ColumnFilter,
    FilterOperator,
    ForceProjection,
    IntegrityTransformation,
)
from data_manipulation.transformation.transform_sql import (
    PreviewResult,
    _cast_expr,  # pyright: ignore[reportPrivateUsage]
    _json_safe,  # pyright: ignore[reportPrivateUsage]
    _parse_srid,  # pyright: ignore[reportPrivateUsage]
    build_transformation_select,
    read_transformed_preview,
    transform_staging_to_final,
)

_PG = postgresql.dialect()


def _staging_table(*, geom: bool = False) -> Table:
    """Hand-built staging table — no reflection, no DB connection."""
    cols = [
        Column("id", Integer),
        Column("lbl", String),
        Column("qty", String),
        Column("active", String),
        Column("secret", String),
        Column("lon", String),
        Column("lat", String),
    ]
    if geom:
        cols.append(Column("geom", String))
    return Table("staging", MetaData(schema="staging"), *cols)


def _compiled(config: IntegrityTransformation | None, *, geom: bool = False) -> str:
    tq = build_transformation_select(_staging_table(geom=geom), config)
    return str(tq.select.compile(dialect=_PG))


# ---------------------------------------------------------------------------
# _parse_srid
# ---------------------------------------------------------------------------


def test_parse_srid_handles_epsg_string() -> None:
    assert _parse_srid("EPSG:4326") == 4326
    assert _parse_srid("epsg: 2154") == 2154


def test_parse_srid_handles_bare_number() -> None:
    assert _parse_srid("3857") == 3857


def test_parse_srid_unknown_returns_zero() -> None:
    assert _parse_srid(None) == 0
    assert _parse_srid("") == 0
    assert _parse_srid("WGS 84") == 0


# ---------------------------------------------------------------------------
# _cast_expr
# ---------------------------------------------------------------------------


def test_cast_expr_boolean_uses_explicit_token_map() -> None:
    sql = _cast_expr("active", CastType.BOOLEAN)
    assert "lower(trim" in sql
    assert "'true'" in sql and "'false'" in sql
    assert "TRUE" in sql and "FALSE" in sql


def test_cast_expr_numeric_coerces_invalid_to_null() -> None:
    sql = _cast_expr("amount", CastType.NUMERIC)
    assert "double precision" in sql
    assert "ELSE NULL" in sql


def test_cast_expr_date_accepts_iso_and_day_first_formats() -> None:
    sql = _cast_expr("when", CastType.DATE)
    assert "::timestamp" in sql
    assert "IS NULL" in sql and "= ''" in sql
    assert "to_timestamp" in sql
    assert "FMDD/FMMM/YYYY" in sql


def test_cast_expr_text_is_simple_cast() -> None:
    assert _cast_expr("name", CastType.TEXT) == '"name"::text'


def test_cast_expr_quotes_identifier_safely() -> None:
    assert _cast_expr('we"ird', CastType.TEXT) == '"we""ird"::text'


# ---------------------------------------------------------------------------
# build_transformation_select
# ---------------------------------------------------------------------------


def test_select_renames_and_excludes() -> None:
    config = IntegrityTransformation(
        columns=[
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="lbl", new_name="label"),
            ColumnConfig(original_name="secret", excluded=True),
        ]
    )
    tq = build_transformation_select(_staging_table(), config)
    assert tq.property_columns == ["id", "label"]
    assert tq.geom_column is None
    sql = str(tq.select.compile(dialect=_PG))
    assert 'AS label' in sql
    assert "secret" not in sql


def test_select_cast_emits_bool_case() -> None:
    config = IntegrityTransformation(
        columns=[ColumnConfig(original_name="active", cast_type=CastType.BOOLEAN)]
    )
    sql = _compiled(config)
    assert "lower(trim" in sql
    assert "THEN TRUE" in sql and "THEN FALSE" in sql


def test_force_projection_existing_geom_uses_transform_and_setsrid_case() -> None:
    config = IntegrityTransformation(
        force_projection=ForceProjection(type="EPSG:3857"),
        columns=[ColumnConfig(original_name="id"), ColumnConfig(original_name="geom")],
    )
    tq = build_transformation_select(_staging_table(geom=True), config)
    assert tq.geom_column == "geom"
    sql = str(tq.select.compile(dialect=_PG))
    assert "ST_Transform" in sql
    assert "ST_SetSRID" in sql  # the SRID-0 branch of the CASE
    assert "ST_SRID" in sql


def test_existing_geom_passthrough_when_no_projection() -> None:
    config = IntegrityTransformation(
        columns=[ColumnConfig(original_name="id"), ColumnConfig(original_name="geom")]
    )
    tq = build_transformation_select(_staging_table(geom=True), config)
    assert tq.geom_column == "geom"
    sql = str(tq.select.compile(dialect=_PG))
    assert "ST_Transform" not in sql
    assert "AS geom" in sql


def test_xy_point_uses_st_makepoint() -> None:
    config = IntegrityTransformation(
        force_projection=ForceProjection(type="EPSG:4326", x_column="lon", y_column="lat"),
        columns=[ColumnConfig(original_name="id")],
    )
    tq = build_transformation_select(_staging_table(), config)
    assert tq.geom_column == "geom"
    compiled = tq.select.compile(dialect=_PG)
    sql = str(compiled)
    assert "ST_MakePoint" in sql
    assert "ST_SetSRID" in sql
    # The SRID is carried as a bound parameter.
    assert 4326 in compiled.params.values()


def test_geom_never_renamed() -> None:
    config = IntegrityTransformation(
        columns=[
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="geom", new_name="shape"),
        ]
    )
    tq = build_transformation_select(_staging_table(geom=True), config)
    assert tq.geom_column == "geom"
    sql = str(tq.select.compile(dialect=_PG))
    assert "shape" not in sql
    assert "AS geom" in sql


def test_missing_column_skipped() -> None:
    config = IntegrityTransformation(
        columns=[
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="does_not_exist"),
        ]
    )
    tq = build_transformation_select(_staging_table(), config)
    assert tq.property_columns == ["id"]


def test_filter_value_is_bound_parameter_not_inlined() -> None:
    config = IntegrityTransformation(
        columns=[
            ColumnConfig(
                original_name="lbl",
                filter=ColumnFilter(operator=FilterOperator.CONTAINS, value="foo"),
            )
        ]
    )
    tq = build_transformation_select(_staging_table(), config)
    compiled = tq.select.compile(dialect=_PG)
    assert "WHERE" in str(compiled).upper()
    # The pattern lives in params, never in the SQL text.
    assert "%foo%" not in str(compiled)
    assert any("%foo%" == v for v in compiled.params.values())


def test_passthrough_config_none_selects_all() -> None:
    tq = build_transformation_select(_staging_table(geom=True), None)
    assert tq.geom_column == "geom"
    assert "id" in tq.property_columns and "geom" not in tq.property_columns


# ---------------------------------------------------------------------------
# transform_staging_to_final — blocker regression + executor ordering
# ---------------------------------------------------------------------------


def _engine_with_conn_spy(row_count: int = 7) -> tuple[MagicMock, MagicMock]:
    engine = MagicMock(spec=Engine)
    engine.dialect = _PG
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    conn.execute.return_value.scalar.return_value = row_count
    return engine, conn


@patch("data_manipulation.transformation.transform_sql.MetaData")
@patch("data_manipulation.transformation.transform_sql.Table")
def test_filter_reaches_ctas_as_bound_parameter(
    mock_table_cls: MagicMock, _mock_metadata: MagicMock
) -> None:
    """BLOCKER REGRESSION: a column filter must appear in the CTAS WHERE clause,
    with the value carried as a bound parameter (not inlined / not dropped)."""
    mock_table_cls.return_value = _staging_table()

    engine, conn = _engine_with_conn_spy()
    config = IntegrityTransformation(
        columns=[
            ColumnConfig(original_name="id"),
            ColumnConfig(
                original_name="lbl",
                filter=ColumnFilter(operator=FilterOperator.CONTAINS, value="foo"),
            ),
        ]
    )

    rows = transform_staging_to_final(
        "staging_tbl", "final_tbl", engine, config,
        staging_schema="staging", final_schema="data", create_id=False,
    )
    assert rows == 7

    assert conn.exec_driver_sql.call_count == 1
    ctas_sql, ctas_params = conn.exec_driver_sql.call_args.args
    assert "CREATE TABLE" in ctas_sql
    assert "WHERE" in ctas_sql.upper()
    assert "%foo%" not in ctas_sql  # value is parameterised
    assert any("%foo%" == v for v in ctas_params.values())


@patch("data_manipulation.transformation.transform_sql.MetaData")
@patch("data_manipulation.transformation.transform_sql.Table")
def test_executor_statement_ordering(
    mock_table_cls: MagicMock, _mock_metadata: MagicMock
) -> None:
    """DROP -> CTAS -> id column -> PK -> CREATE INDEX (GIST) -> count."""
    mock_table_cls.return_value = _staging_table(geom=True)

    engine, conn = _engine_with_conn_spy(row_count=3)
    config = IntegrityTransformation(
        columns=[ColumnConfig(original_name="id"), ColumnConfig(original_name="geom")]
    )

    transform_staging_to_final(
        "staging_tbl", "final_tbl", engine, config,
        staging_schema="staging", final_schema="data", create_id=True,
    )

    # text()-based statements go through conn.execute; CTAS goes through exec_driver_sql.
    executed = [str(c.args[0]) for c in conn.execute.call_args_list]
    drop_idx = next(i for i, s in enumerate(executed) if "DROP TABLE IF EXISTS" in s)
    id_idx = next(i for i, s in enumerate(executed) if "ADD COLUMN id_datafeeder UUID" in s)
    pk_idx = next(i for i, s in enumerate(executed) if "PRIMARY KEY (id_datafeeder)" in s)
    index_idx = next(i for i, s in enumerate(executed) if "USING GIST" in s)
    count_idx = next(i for i, s in enumerate(executed) if "count(*)" in s)

    assert drop_idx < id_idx < pk_idx < index_idx < count_idx
    assert conn.exec_driver_sql.call_count == 1  # the CTAS
    assert 'idx_final_tbl_geom' in executed[index_idx]


@patch("data_manipulation.transformation.transform_sql.MetaData")
@patch("data_manipulation.transformation.transform_sql.Table")
def test_no_geom_skips_index(
    mock_table_cls: MagicMock, _mock_metadata: MagicMock
) -> None:
    mock_table_cls.return_value = _staging_table(geom=False)
    engine, conn = _engine_with_conn_spy()
    config = IntegrityTransformation(columns=[ColumnConfig(original_name="id")])

    transform_staging_to_final("staging_tbl", "final_tbl", engine, config, create_id=True)

    executed = [str(c.args[0]) for c in conn.execute.call_args_list]
    assert not any("USING GIST" in s for s in executed)


# ---------------------------------------------------------------------------
# read_transformed_preview
# ---------------------------------------------------------------------------


@patch("data_manipulation.transformation.transform_sql.MetaData")
@patch("data_manipulation.transformation.transform_sql.Table")
def test_preview_shape_and_json_safe(
    mock_table_cls: MagicMock, _mock_metadata: MagicMock
) -> None:
    mock_table_cls.return_value = _staging_table(geom=True)

    engine = MagicMock(spec=Engine)
    engine.dialect = _PG
    conn = MagicMock()
    engine.connect.return_value.__enter__.return_value = conn

    mappings = [
        {
            "id": 1,
            "qty": Decimal("3.5"),
            "active": datetime.datetime(2024, 1, 2, 8, 30),
            "geom": "POINT(1 2)",
            "__geojson__": '{"type": "Point", "coordinates": [1, 2]}',
        }
    ]
    conn.execute.return_value.mappings.return_value = mappings

    result = read_transformed_preview("staging_tbl", engine, None, schema="staging", limit=5)

    assert isinstance(result, PreviewResult)
    assert result.is_geographic is True
    assert result.geojson is not None
    assert result.geojson["type"] == "FeatureCollection"
    assert len(result.geojson["features"]) == 1
    feature = result.geojson["features"][0]
    assert feature["geometry"] == {"type": "Point", "coordinates": [1, 2]}
    # __geojson__ is stripped from the tabular row; geom stays as the WKT string.
    row = result.rows[0]
    assert "__geojson__" not in row
    assert row["geom"] == "POINT(1 2)"
    # _json_safe conversions:
    assert row["qty"] == 3.5 and isinstance(row["qty"], float)
    assert row["active"] == "2024-01-02T08:30:00"


def test_json_safe_conversions() -> None:
    assert _json_safe(None) is None
    assert _json_safe(Decimal("1.25")) == 1.25
    assert _json_safe(datetime.date(2024, 1, 2)) == "2024-01-02"
    assert _json_safe(b"\x00\xff") == "00ff"
    assert _json_safe("plain") == "plain"
