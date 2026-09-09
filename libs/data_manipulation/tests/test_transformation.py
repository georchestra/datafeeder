"""Tests for the SQL-native transformation builder.

These tests construct ``Table`` objects in memory (no database needed) and
assert on the compiled PostgreSQL SQL produced by
:func:`build_transformation_select`.  This is the single canonical builder used
by both the process path (``CREATE TABLE AS``) and the preview path, so
verifying its output guarantees preview/process parity (FR-021).
"""

from unittest.mock import MagicMock, patch

from sqlalchemy import Column, Integer, MetaData, Table, Text
from sqlalchemy.dialects import postgresql

from data_manipulation.models import (
    CastType,
    ColumnConfig,
    ColumnFilter,
    FilterOperator,
    ForceProjection,
    IntegrityTransformation,
)
from data_manipulation.transformation.sql_transform import (
    _parse_srid,  # type: ignore[reportPrivateUsage]
    build_transformation_select,
    transform_staging_to_final,
)


def _staging_table(*, with_geom: bool = True) -> Table:
    metadata = MetaData(schema="staging")
    cols = [
        Column("name", Text),
        Column("population", Text),
        Column("active", Text),
        Column("created", Text),
        Column("lon", Text),
        Column("lat", Text),
        Column("ratio", Integer),
    ]
    if with_geom:
        cols.append(Column("geom", Text))
    return Table("places", metadata, *cols)


def _compile(table: Table, config: IntegrityTransformation | None) -> str:
    tq = build_transformation_select(table, config)
    return str(
        tq.select.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )


class TestParseSrid:
    def test_parses_epsg_prefixed(self) -> None:
        assert _parse_srid("EPSG:2154") == 2154

    def test_parses_bare_code(self) -> None:
        assert _parse_srid("4326") == 4326

    def test_empty_returns_none(self) -> None:
        assert _parse_srid("") is None
        assert _parse_srid(None) is None

    def test_unparseable_returns_none(self) -> None:
        assert _parse_srid("not-a-crs") is None


class TestPassthrough:
    def test_none_config_selects_all_columns(self) -> None:
        table = _staging_table()
        tq = build_transformation_select(table, None)
        # geom is emitted separately and excluded from property columns
        assert "geom" not in tq.property_columns
        assert tq.geom_column == "geom"
        assert "name" in tq.property_columns
        assert "population" in tq.property_columns

    def test_no_geom_table_has_no_geom_column(self) -> None:
        table = _staging_table(with_geom=False)
        tq = build_transformation_select(table, None)
        assert tq.geom_column is None


class TestColumnSelection:
    def test_excluded_column_is_omitted(self) -> None:
        table = _staging_table()
        config = IntegrityTransformation(
            columns=[
                ColumnConfig(original_name="name"),
                ColumnConfig(original_name="population", excluded=True),
            ]
        )
        sql = _compile(table, config)
        assert "name" in sql
        assert "population" not in sql

    def test_rename_uses_new_name_label(self) -> None:
        table = _staging_table()
        config = IntegrityTransformation(
            columns=[ColumnConfig(original_name="name", new_name="label")]
        )
        tq = build_transformation_select(table, config)
        assert "label" in tq.property_columns
        assert "name" not in tq.property_columns


class TestCasts:
    def test_boolean_cast_uses_helper(self) -> None:
        table = _staging_table()
        config = IntegrityTransformation(
            columns=[ColumnConfig(original_name="active", cast_type=CastType.BOOLEAN)]
        )
        sql = _compile(table, config)
        assert "datafeeder_to_bool" in sql

    def test_numeric_cast_uses_helper(self) -> None:
        table = _staging_table()
        config = IntegrityTransformation(
            columns=[ColumnConfig(original_name="population", cast_type=CastType.NUMERIC)]
        )
        sql = _compile(table, config)
        assert "datafeeder_to_numeric" in sql

    def test_date_cast_uses_helper(self) -> None:
        table = _staging_table()
        config = IntegrityTransformation(
            columns=[ColumnConfig(original_name="created", cast_type=CastType.DATE)]
        )
        sql = _compile(table, config)
        assert "datafeeder_to_date" in sql

    def test_text_cast_uses_sql_cast(self) -> None:
        table = _staging_table()
        config = IntegrityTransformation(
            columns=[ColumnConfig(original_name="ratio", cast_type=CastType.TEXT)]
        )
        sql = _compile(table, config)
        assert "CAST" in sql.upper()


class TestFilters:
    def test_contains_filter_emits_where_ilike(self) -> None:
        table = _staging_table()
        config = IntegrityTransformation(
            columns=[
                ColumnConfig(
                    original_name="name",
                    filter=ColumnFilter(operator=FilterOperator.CONTAINS, value="paris"),
                )
            ]
        )
        sql = _compile(table, config).upper()
        assert "WHERE" in sql
        assert "ILIKE" in sql

    def test_filter_value_is_bound_not_inlined(self) -> None:
        table = _staging_table()
        config = IntegrityTransformation(
            columns=[
                ColumnConfig(
                    original_name="name",
                    filter=ColumnFilter(operator=FilterOperator.EXACTLY, value="paris"),
                )
            ]
        )
        sql = _compile(table, config)
        # value must be a bound parameter, never inlined into the SQL text
        assert "paris" not in sql


class TestProjection:
    def test_force_projection_relabels_with_setsrid_not_transform(self) -> None:
        """force_projection mirrors geopandas set_crs: relabel, not reproject."""
        table = _staging_table()
        config = IntegrityTransformation(
            columns=[
                ColumnConfig(original_name="name"),
                ColumnConfig(original_name="geom"),
            ],
            force_projection=ForceProjection(type="EPSG:2154"),
        )
        tq = build_transformation_select(table, config)
        compiled = tq.select.compile(dialect=postgresql.dialect())
        sql = str(compiled)
        assert "ST_SetSRID" in sql
        assert 2154 in compiled.params.values()
        assert "ST_Transform" not in sql

    def test_xy_columns_build_point(self) -> None:
        table = _staging_table(with_geom=False)
        config = IntegrityTransformation(
            columns=[ColumnConfig(original_name="name")],
            force_projection=ForceProjection(type="EPSG:4326", x_column="lon", y_column="lat"),
        )
        tq = build_transformation_select(table, config)
        sql = _compile(table, config)
        assert tq.geom_column == "geom"
        assert "ST_MakePoint" in sql
        assert "ST_SetSRID" in sql


class _RecordingConnection:
    """Captures the SQL transform_staging_to_final executes, without a database."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    def execute(self, statement: object, *args: object, **kwargs: object) -> MagicMock:
        self.statements.append(str(statement))
        result = MagicMock()
        result.scalar.return_value = 1
        return result

    def exec_driver_sql(self, statement: str, *args: object, **kwargs: object) -> MagicMock:
        self.statements.append(statement)
        return MagicMock()

    def commit(self) -> None:
        pass

    def __enter__(self) -> "_RecordingConnection":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _run_transform(table: Table) -> list[str]:
    """Run transform_staging_to_final against *table* and return executed SQL."""
    conn = _RecordingConnection()
    engine = MagicMock()
    engine.connect.return_value = conn
    engine.dialect = postgresql.dialect()

    with patch("data_manipulation.transformation.sql_transform.Table", return_value=table):
        transform_staging_to_final(
            staging_table="places",
            final_table="final_places",
            engine=engine,
            config=None,
            staging_schema="staging",
            final_schema="data",
            create_id=False,
        )
    return conn.statements


class TestSpatialIndex:
    """CREATE TABLE AS copies no indexes, so the spatial index must be recreated.

    Without it every bbox query on the published table (GeoServer WMS/WFS)
    degrades to a sequential scan.
    """

    def test_geographic_table_gets_gist_index(self) -> None:
        sql = " ".join(_run_transform(_staging_table(with_geom=True)))
        assert "CREATE INDEX" in sql
        assert "USING GIST" in sql

    def test_index_name_matches_the_postgis_convention(self) -> None:
        # to_postgis created idx_<table>_<geom_col>; keep that name.
        sql = " ".join(_run_transform(_staging_table(with_geom=True)))
        assert "idx_final_places_geom" in sql

    def test_tabular_table_gets_no_index(self) -> None:
        sql = " ".join(_run_transform(_staging_table(with_geom=False)))
        assert "CREATE INDEX" not in sql
