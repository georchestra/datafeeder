"""Tests for the SQL-native transformation builder.

These tests construct ``Table`` objects in memory (no database needed) and
assert on the compiled PostgreSQL SQL produced by
:func:`build_transformation_select`.  This is the single canonical builder used
by both the process path (``CREATE TABLE AS``) and the preview path, so
verifying its output guarantees preview/process parity (FR-021).
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, Text
from sqlalchemy.dialects import postgresql

from data_manipulation.models import (
    CastType,
    ColumnConfig,
    ColumnFilter,
    FilterOperator,
    ForceProjection,
    IntegrityTransformation,
    JoinConfig,
)
from data_manipulation.transformation.sql_transform import (
    _parse_srid,  # type: ignore[reportPrivateUsage]
    build_transformation_select,
    reflect_join_table,
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
        """force_projection relabels the SRID, it does not reproject."""
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


def _communes_table() -> Table:
    metadata = MetaData(schema="org_a")
    return Table(
        "communes",
        metadata,
        Column("insee", Text),
        Column("name", Text),
        Column("dept", Integer),
        Column("geom", Text),
        Column("id_datafeeder", Text),
    )


def _join(
    columns: list[str] | None = None, staging_columns: list[ColumnConfig] | None = None
) -> IntegrityTransformation:
    join = JoinConfig(
        table_schema="org_a",
        table_name="communes",
        source_column="ratio",
        target_column="insee",
        columns=["insee", "dept"] if columns is None else columns,
    )
    return IntegrityTransformation(columns=staging_columns, join=join)


def _staging_columns(**overrides: ColumnConfig) -> list[ColumnConfig]:
    """One ColumnConfig per staging column, replaced by *overrides* by original name."""
    return [
        overrides.get(col.name, ColumnConfig(original_name=col.name)) for col in _staging_table().c
    ]


class TestJoin:
    def test_left_join_on_keys_compared_as_text(self) -> None:
        tq = build_transformation_select(_staging_table(), _join(), _communes_table())
        sql = str(tq.select.compile(dialect=postgresql.dialect()))
        assert "LEFT OUTER JOIN org_a.communes" in sql
        assert "CAST(staging.places.ratio AS TEXT) = CAST(org_a.communes.insee AS TEXT)" in sql

    def test_adds_joined_columns_after_staging_ones(self) -> None:
        tq = build_transformation_select(_staging_table(), _join(), _communes_table())
        assert tq.property_columns[-2:] == ["insee", "dept"]
        assert tq.geom_column == "geom"
        sql = str(tq.select.compile(dialect=postgresql.dialect()))
        assert "org_a.communes.dept AS dept" in sql

    def test_empty_columns_means_no_join(self) -> None:
        config = _join(columns=[])
        tq = build_transformation_select(_staging_table(), config, None)
        sql = str(tq.select.compile(dialect=postgresql.dialect()))
        assert "JOIN" not in sql
        assert (
            tq.property_columns
            == build_transformation_select(_staging_table(), None).property_columns
        )

    def test_empty_columns_does_not_reflect(self) -> None:
        engine = MagicMock()
        assert reflect_join_table(_join(columns=[]).join, engine) is None

    def test_staging_geom_is_qualified(self) -> None:
        tq = build_transformation_select(_staging_table(), _join(), _communes_table())
        sql = str(tq.select.compile(dialect=postgresql.dialect()))
        assert '"places"."geom" AS geom' in sql

    def test_name_clash_raises(self) -> None:
        with pytest.raises(ValueError, match="clash"):
            build_transformation_select(
                _staging_table(), _join(columns=["name"]), _communes_table()
            )

    def test_clash_uses_renamed_staging_column(self) -> None:
        staging = _staging_columns(
            population=ColumnConfig(original_name="population", new_name="dept")
        )
        with pytest.raises(ValueError, match="clash"):
            build_transformation_select(
                _staging_table(), _join(staging_columns=staging), _communes_table()
            )

    def test_renaming_staging_column_avoids_clash(self) -> None:
        staging = _staging_columns(name=ColumnConfig(original_name="name", new_name="nom"))
        config = _join(columns=["name"], staging_columns=staging)
        tq = build_transformation_select(_staging_table(), config, _communes_table())
        assert "nom" in tq.property_columns
        assert tq.property_columns[-1] == "name"

    def test_excluded_staging_column_does_not_clash(self) -> None:
        staging = _staging_columns(name=ColumnConfig(original_name="name", excluded=True))
        config = _join(columns=["name"], staging_columns=staging)
        tq = build_transformation_select(_staging_table(), config, _communes_table())
        assert tq.property_columns.count("name") == 1

    def test_joined_id_datafeeder_clashes_with_final_primary_key(self) -> None:
        with pytest.raises(ValueError, match="clash"):
            build_transformation_select(
                _staging_table(), _join(columns=["id_datafeeder"]), _communes_table()
            )

    def test_joined_geom_clashes_with_kept_staging_geom(self) -> None:
        with pytest.raises(ValueError, match="clash"):
            build_transformation_select(
                _staging_table(), _join(columns=["geom"]), _communes_table()
            )

    def test_joined_geom_clashes_with_built_point(self) -> None:
        config = _join(columns=["geom"])
        config.force_projection = ForceProjection(type="EPSG:4326", x_column="lon", y_column="lat")
        with pytest.raises(ValueError, match="clash"):
            build_transformation_select(_staging_table(), config, _communes_table())

    def test_joined_geom_replaces_excluded_staging_geom(self) -> None:
        staging = _staging_columns(geom=ColumnConfig(original_name="geom", excluded=True))
        config = _join(columns=["geom"], staging_columns=staging)
        config.force_projection = ForceProjection(type="EPSG:2154")
        tq = build_transformation_select(_staging_table(), config, _communes_table())
        assert tq.geom_column == "geom"
        assert "geom" not in tq.property_columns
        sql = str(tq.select.compile(dialect=postgresql.dialect()))
        assert 'ST_SetSRID("communes"."geom"' in sql
        assert '"places"."geom"' not in sql

    def test_joined_geom_without_staging_geom(self) -> None:
        config = _join(columns=["geom"])
        tq = build_transformation_select(_staging_table(with_geom=False), config, _communes_table())
        assert tq.geom_column == "geom"

    def test_join_requires_join_table(self) -> None:
        with pytest.raises(ValueError, match="join_table"):
            build_transformation_select(_staging_table(), _join(), None)

    def test_unknown_column_raises(self) -> None:
        config = _join(columns=["dept", "missing"])
        with pytest.raises(ValueError, match="missing"):
            build_transformation_select(_staging_table(), config, _communes_table())

    def test_unknown_join_key_raises(self) -> None:
        config = IntegrityTransformation(
            join=JoinConfig(
                table_schema="org_a",
                table_name="communes",
                source_column="nope",
                target_column="insee",
                columns=["dept"],
            )
        )
        with pytest.raises(ValueError, match="nope"):
            build_transformation_select(_staging_table(), config, _communes_table())


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
        # PostGIS naming convention: idx_<table>_<geom_col>.
        sql = " ".join(_run_transform(_staging_table(with_geom=True)))
        assert "idx_final_places_geom" in sql

    def test_tabular_table_gets_no_index(self) -> None:
        sql = " ".join(_run_transform(_staging_table(with_geom=False)))
        assert "CREATE INDEX" not in sql
