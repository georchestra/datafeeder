"""Tests for the SQL-only transform path (no PG required, mocked engine)."""

from unittest.mock import MagicMock, patch

from sqlalchemy.engine import Engine

from data_manipulation.models import (
    CastType,
    ColumnConfig,
    ForceProjection,
    IntegrityTransformation,
)
from data_manipulation.transformation.transform_sql import (
    _build_geom_expression,  # pyright: ignore[reportPrivateUsage]
    _build_select_expressions,  # pyright: ignore[reportPrivateUsage]
    _cast_expr,  # pyright: ignore[reportPrivateUsage]
    _parse_srid,  # pyright: ignore[reportPrivateUsage]
    transform_in_place_via_sql,
)


def test_parse_srid_handles_epsg_string() -> None:
    assert _parse_srid("EPSG:4326") == 4326
    assert _parse_srid("epsg: 2154") == 2154


def test_parse_srid_handles_bare_number() -> None:
    assert _parse_srid("3857") == 3857


def test_parse_srid_unknown_returns_zero() -> None:
    assert _parse_srid(None) == 0
    assert _parse_srid("") == 0
    assert _parse_srid("WGS 84") == 0


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
    # Empty strings and NULLs map to NULL, ISO 8601 routes through ::timestamp,
    # day-first formats go through to_timestamp().
    assert "IS NULL" in sql and "= ''" in sql
    assert "to_timestamp" in sql
    assert "FMDD/FMMM/YYYY" in sql


def test_cast_expr_text_is_simple_cast() -> None:
    assert _cast_expr("name", CastType.TEXT) == '"name"::text'


def test_build_select_expressions_renames_and_casts() -> None:
    cfgs = [
        ColumnConfig(original_name="id"),
        ColumnConfig(original_name="lbl", new_name="label"),
        ColumnConfig(original_name="qty", cast_type=CastType.NUMERIC),
        ColumnConfig(original_name="secret", excluded=True),
    ]
    parts = _build_select_expressions(cfgs, geom_expr=None)
    assert any(p == '"id" AS "id"' for p in parts)
    assert any(p == '"lbl" AS "label"' for p in parts)
    assert any('"qty"' in p and 'AS "qty"' in p for p in parts)
    assert not any("secret" in p for p in parts)


def test_build_select_expressions_appends_geom_expr() -> None:
    parts = _build_select_expressions(
        [ColumnConfig(original_name="id")],
        geom_expr="ST_SetSRID(ST_MakePoint(1, 2), 4326)",
    )
    assert parts[-1] == 'ST_SetSRID(ST_MakePoint(1, 2), 4326) AS "geom"'


def _staging_table_mock(*, has_geom: bool) -> MagicMock:
    table = MagicMock()

    def _contains(key: object) -> bool:
        return bool(has_geom and key == "geom")

    table.c.__contains__ = MagicMock(side_effect=_contains)
    return table


def test_build_geom_expression_xy_to_point() -> None:
    config = IntegrityTransformation(
        force_projection=ForceProjection(type="EPSG:4326", x_column="lon", y_column="lat")
    )
    expr = _build_geom_expression(_staging_table_mock(has_geom=False), config)
    assert expr is not None
    assert "ST_MakePoint" in expr
    assert "ST_SetSRID" in expr
    assert "4326" in expr
    assert '"lon"' in expr and '"lat"' in expr


def test_build_geom_expression_reprojects_existing_geom() -> None:
    config = IntegrityTransformation(force_projection=ForceProjection(type="EPSG:3857"))
    expr = _build_geom_expression(_staging_table_mock(has_geom=True), config)
    assert expr is not None
    assert "ST_Transform" in expr
    assert "3857" in expr


def test_build_geom_expression_passes_geom_through_when_no_reproj() -> None:
    config = IntegrityTransformation()
    expr = _build_geom_expression(_staging_table_mock(has_geom=True), config)
    assert expr == '"geom"'


def test_build_geom_expression_tabular_returns_none() -> None:
    config = IntegrityTransformation()
    expr = _build_geom_expression(_staging_table_mock(has_geom=False), config)
    assert expr is None


@patch("data_manipulation.transformation.transform_sql.Table")
@patch("data_manipulation.transformation.transform_sql.MetaData")
def test_transform_in_place_executes_create_table_as_select(
    _mock_metadata: MagicMock, mock_table_cls: MagicMock
) -> None:
    """End-to-end shape: builds and runs CREATE TABLE … AS SELECT against a mocked engine."""
    staging = MagicMock()
    staging.c.__contains__ = MagicMock(return_value=False)
    staging.c = MagicMock()
    staging.c.__iter__ = MagicMock(return_value=iter([]))
    staging.c.__contains__ = MagicMock(return_value=False)
    mock_table_cls.return_value = staging

    engine = MagicMock(spec=Engine)
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    conn.execute.return_value.scalar.return_value = 42

    config = IntegrityTransformation(
        columns=[
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="amount", cast_type=CastType.NUMERIC),
        ]
    )

    rows = transform_in_place_via_sql(
        staging_table_name="staging_tbl",
        staging_schema="staging",
        target_table_name="final_tbl",
        target_schema="data",
        engine=engine,
        config=config,
        create_id=True,
    )
    assert rows == 42

    executed = [str(c.args[0]) for c in conn.execute.call_args_list]
    assert any("DROP TABLE IF EXISTS" in s and "final_tbl" in s for s in executed)
    assert any("CREATE TABLE" in s and "AS SELECT" in s for s in executed)
    assert any("ADD COLUMN id_datafeeder UUID" in s for s in executed)
    assert any("PRIMARY KEY (id_datafeeder)" in s for s in executed)
