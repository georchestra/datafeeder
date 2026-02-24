"""Unit tests for column action transformations"""


from unittest.mock import patch

import geopandas as gpd
import pandas as pd
from sqlalchemy import (
    BinaryExpression,
    Column,
    Integer,
    MetaData,
    Select,
    String,
    Table,
    create_engine,
)
from sqlalchemy.sql.elements import Cast

from data_manipulation.ingestion import read_and_transform_data, read_data_from_postgis
from data_manipulation.models import (
    CastType,
    ColumnConfig,
    ColumnFilter,
    FilterOperator,
    ForceProjection,
    IntegrityTransformation,
)
from data_manipulation.transformation.filter_sql import build_sql_column_ops
from data_manipulation.transformation.transform import apply_transformations
from data_manipulation.transformation.transform_columns import cast_column_types, rename_columns

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_table() -> Table:
    """Return an in-memory SQLAlchemy Table without requiring a DB connection."""
    metadata = MetaData()
    return Table(
        "test_table",
        metadata,
        Column("id", Integer),
        Column("name", String),
        Column("city", String),
        Column("age", Integer),
    )


def _sqlite_engine_with_data():
    """Return a SQLite in-memory engine with a simple test table pre-populated."""
    engine = create_engine("sqlite://")
    metadata = MetaData()
    tbl = Table(
        "staging",
        metadata,
        Column("id", Integer),
        Column("name", String),
        Column("city", String),
    )
    metadata.create_all(engine)

    rows = [
        {"id": i, "name": f"name_{i}", "city": "Paris" if i > 10 else "Lyon"} for i in range(1, 21)
    ]
    with engine.connect() as conn:
        conn.execute(tbl.insert(), rows)
        conn.commit()

    return engine


# ===========================================================================
# Tests for build_sql_column_ops
# ===========================================================================


class TestBuildSqlColumnOps:
    """Unit tests for build_sql_column_ops."""

    def test_empty_columns_returns_all_cols_no_where(self):
        """Empty column list → (all_cols, [])."""
        table = _make_table()
        select_cols, where_clauses = build_sql_column_ops([], table)

        assert [c.key for c in select_cols] == ["id", "name", "city", "age"]
        assert where_clauses == []

    def test_excluded_column_absent_from_select_cols(self):
        """Excluded column not present in select_cols."""
        table = _make_table()
        columns = [
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="name", excluded=True),
            ColumnConfig(original_name="city"),
        ]
        select_cols, _ = build_sql_column_ops(columns, table)

        col_keys = [c.key for c in select_cols]
        assert "name" not in col_keys
        assert "id" in col_keys
        assert "city" in col_keys

    def test_no_filter_produces_no_where_clause(self):
        """Non-excluded column without filter → no where clause."""
        table = _make_table()
        columns = [ColumnConfig(original_name="name")]

        select_cols, where_clauses = build_sql_column_ops(columns, table)

        assert len(select_cols) == 1
        assert where_clauses == []

    def test_excluded_with_filter_produces_no_where_clause(self):
        """excluded=True column with filter → no where clause AND absent from select_cols."""
        table = _make_table()
        columns = [
            ColumnConfig(
                original_name="name",
                excluded=True,
                filter=ColumnFilter(operator=FilterOperator.EXACTLY, value="Alice"),
            )
        ]
        select_cols, where_clauses = build_sql_column_ops(columns, table)

        assert select_cols == []
        assert where_clauses == []

    def test_exactly_operator_produces_binary_expression(self):
        """EXACTLY operator → BinaryExpression with Cast(Text) operand."""
        table = _make_table()
        columns = [
            ColumnConfig(
                original_name="name",
                filter=ColumnFilter(operator=FilterOperator.EXACTLY, value="Alice"),
            )
        ]
        _, where_clauses = build_sql_column_ops(columns, table)

        assert len(where_clauses) == 1
        expr = where_clauses[0]
        assert isinstance(expr, BinaryExpression)
        # Left side must be a Cast expression
        assert isinstance(expr.left, Cast)

    def test_contains_operator_produces_like_expression(self):
        """CONTAINS operator → LIKE BinaryExpression."""
        table = _make_table()
        columns = [
            ColumnConfig(
                original_name="city",
                filter=ColumnFilter(operator=FilterOperator.CONTAINS, value="Par"),
            )
        ]
        _, where_clauses = build_sql_column_ops(columns, table)

        assert len(where_clauses) == 1
        compiled = where_clauses[0].compile(compile_kwargs={"literal_binds": True})
        assert "LIKE" in str(compiled).upper()

    def test_starts_with_operator_produces_like_expression(self):
        """STARTS_WITH operator → LIKE BinaryExpression."""
        table = _make_table()
        columns = [
            ColumnConfig(
                original_name="name",
                filter=ColumnFilter(operator=FilterOperator.STARTS_WITH, value="Al"),
            )
        ]
        _, where_clauses = build_sql_column_ops(columns, table)

        assert len(where_clauses) == 1
        compiled = where_clauses[0].compile(compile_kwargs={"literal_binds": True})
        assert "LIKE" in str(compiled).upper()

    def test_filter_value_not_inlined_as_literal(self):
        """Filter value is a bound parameter, not inlined in SQL text."""
        table = _make_table()
        filter_value = "SuperSecretValue"
        columns = [
            ColumnConfig(
                original_name="name",
                filter=ColumnFilter(operator=FilterOperator.EXACTLY, value=filter_value),
            )
        ]
        _, where_clauses = build_sql_column_ops(columns, table)

        # Compile WITHOUT literal_binds — value must appear as :param placeholder
        compiled = where_clauses[0].compile(compile_kwargs={"literal_binds": False})
        sql_text = str(compiled)
        assert filter_value not in sql_text, (
            f"Filter value '{filter_value}' was inlined in SQL text: {sql_text}"
        )

    def test_contains_filter_value_not_inlined(self):
        """CONTAINS filter — pattern with % delimiters is a bound param."""
        table = _make_table()
        filter_value = "InjectionAttempt"
        columns = [
            ColumnConfig(
                original_name="city",
                filter=ColumnFilter(operator=FilterOperator.CONTAINS, value=filter_value),
            )
        ]
        _, where_clauses = build_sql_column_ops(columns, table)

        compiled = where_clauses[0].compile(compile_kwargs={"literal_binds": False})
        sql_text = str(compiled)
        assert filter_value not in sql_text

    def test_multiple_filters_produce_multiple_where_clauses(self):
        """Multiple non-excluded columns with filters → one clause each."""
        table = _make_table()
        columns = [
            ColumnConfig(
                original_name="name",
                filter=ColumnFilter(operator=FilterOperator.STARTS_WITH, value="A"),
            ),
            ColumnConfig(
                original_name="city",
                filter=ColumnFilter(operator=FilterOperator.CONTAINS, value="Paris"),
            ),
        ]
        select_cols, where_clauses = build_sql_column_ops(columns, table)

        assert len(select_cols) == 2
        assert len(where_clauses) == 2


# ===========================================================================
# Tests for read_data_from_postgis with columns param
# ===========================================================================


class TestReadDataFromPostgisWithColumns:
    """Integration-style tests for read_data_from_postgis with columns param."""

    def test_filter_applied_before_limit(self):
        """Rows 11-20 match 'Paris'; with limit=10, all 10 returned rows match."""
        engine = _sqlite_engine_with_data()
        columns = [
            ColumnConfig(
                original_name="city",
                filter=ColumnFilter(operator=FilterOperator.EXACTLY, value="Paris"),
            ),
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="name"),
        ]

        result = read_data_from_postgis("staging", engine, columns=columns, limit=10)

        # All returned rows must match the filter — filter is before LIMIT
        assert len(result) == 10
        assert all(result["city"] == "Paris")

    def test_excluded_column_absent_from_result(self):
        """Excluded column is not present in the returned DataFrame."""
        engine = _sqlite_engine_with_data()
        columns = [
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="name"),
            ColumnConfig(original_name="city", excluded=True),
        ]

        result = read_data_from_postgis("staging", engine, columns=columns)

        assert "city" not in result.columns
        assert "id" in result.columns
        assert "name" in result.columns

    def test_limit_none_returns_all_matching_rows(self):
        """limit=None returns all rows matching the filter (no truncation)."""
        engine = _sqlite_engine_with_data()
        columns = [
            ColumnConfig(
                original_name="city",
                filter=ColumnFilter(operator=FilterOperator.EXACTLY, value="Paris"),
            ),
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="name"),
        ]

        result = read_data_from_postgis("staging", engine, columns=columns, limit=None)

        assert len(result) == 10
        assert all(result["city"] == "Paris")

    def test_no_columns_param_returns_all_rows(self):
        """No columns param → all rows and columns returned."""
        engine = _sqlite_engine_with_data()

        result = read_data_from_postgis("staging", engine)

        assert len(result) == 20
        assert "id" in result.columns
        assert "name" in result.columns
        assert "city" in result.columns

    def test_pd_read_sql_receives_select_object(self):
        """pd.read_sql receives a Select object, not a compiled string."""
        engine = _sqlite_engine_with_data()
        columns = [ColumnConfig(original_name="name"), ColumnConfig(original_name="id")]

        with patch("data_manipulation.ingestion.pd.read_sql") as mock_read_sql:
            mock_read_sql.return_value = pd.DataFrame({"name": ["name_1"], "id": [1]})
            read_data_from_postgis("staging", engine, columns=columns)

        assert mock_read_sql.called
        first_arg = mock_read_sql.call_args[0][0]
        assert isinstance(first_arg, Select), (
            f"Expected Select object but got {type(first_arg).__name__}"
        )

    def test_all_columns_excluded_returns_empty_dataframe(self):
        """Edge case: all columns excluded → returns empty DataFrame."""
        engine = _sqlite_engine_with_data()
        columns = [
            ColumnConfig(original_name="id", excluded=True),
            ColumnConfig(original_name="name", excluded=True),
            ColumnConfig(original_name="city", excluded=True),
        ]

        result = read_data_from_postgis("staging", engine, columns=columns)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_filter_before_limit_confirms_no_pre_limit(self):
        """T006a (1 extra): confirm filter-then-limit vs limit-then-filter difference.

        Table has 20 rows; rows 1-10 have city='Lyon', rows 11-20 have city='Paris'.
        With limit=5 and filter city='Paris':
        - Correct (filter first):  returns 5 Paris rows
        - Wrong  (limit first):    limit=5 would capture only Lyon rows → 0 Paris rows
        """
        engine = _sqlite_engine_with_data()
        columns = [
            ColumnConfig(
                original_name="city",
                filter=ColumnFilter(operator=FilterOperator.EXACTLY, value="Paris"),
            ),
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="name"),
        ]

        result = read_data_from_postgis("staging", engine, columns=columns, limit=5)

        assert len(result) == 5
        assert all(result["city"] == "Paris"), "limit-then-filter bug: 0 Paris rows returned"


# ===========================================================================
# Tests for read_and_transform_data with column transformations
# ===========================================================================


class TestReadAndTransformData:
    """Tests for read_and_transform_data pipeline."""

    def test_config_none_returns_raw_data(self):
        """config=None → raw data returned unchanged."""
        engine = _sqlite_engine_with_data()

        result = read_and_transform_data("staging", engine, config=None)

        assert len(result) == 20
        assert list(result.columns) == ["id", "name", "city"]

    def test_end_to_end_filter_exclude_rename_cast(self):
        """filter+exclude at SQL, rename+cast at Python — matching manual steps."""
        engine = _sqlite_engine_with_data()
        columns = [
            ColumnConfig(
                original_name="city",
                filter=ColumnFilter(operator=FilterOperator.EXACTLY, value="Paris"),
                new_name="ville",
            ),
            ColumnConfig(original_name="id", cast_type=CastType.TEXT),
            ColumnConfig(original_name="name", excluded=True),
        ]
        config = IntegrityTransformation(columns=columns)

        result = read_and_transform_data("staging", engine, config=config)

        # 10 Paris rows
        assert len(result) == 10
        # Excluded column absent
        assert "name" not in result.columns
        # Renamed column present
        assert "ville" in result.columns
        assert "city" not in result.columns
        # Cast applied: id should be string
        assert result["id"].dtype == object or pd.api.types.is_string_dtype(result["id"])

    def test_limit_10_vs_none_filter_then_limit(self):
        """limit=10 vs limit=None confirms LIMIT applied after filters."""
        engine = _sqlite_engine_with_data()
        columns = [
            ColumnConfig(
                original_name="city",
                filter=ColumnFilter(operator=FilterOperator.EXACTLY, value="Paris"),
            ),
            ColumnConfig(original_name="id"),
            ColumnConfig(original_name="name"),
        ]
        config = IntegrityTransformation(columns=columns)

        result_limited = read_and_transform_data("staging", engine, config=config, limit=10)
        result_full = read_and_transform_data("staging", engine, config=config, limit=None)

        assert len(result_limited) == 10
        assert len(result_full) == 10  # Only 10 matching rows exist
        assert all(result_limited["city"] == "Paris")
        assert all(result_full["city"] == "Paris")


# ===========================================================================
# Tests for rename_columns and cast_column_types
# ===========================================================================


class TestRenameColumns:
    """Unit tests for rename_columns."""

    def test_rename_changes_column_name(self):
        """rename_columns renames columns according to new_name."""
        df = pd.DataFrame({"col_a": [1, 2], "col_b": ["x", "y"]})
        columns = [
            ColumnConfig(original_name="col_a", new_name="column_a"),
            ColumnConfig(original_name="col_b"),
        ]

        result = rename_columns(df, columns)

        assert "column_a" in result.columns
        assert "col_a" not in result.columns
        assert "col_b" in result.columns  # unchanged

    def test_no_rename_when_new_name_is_none(self):
        """Columns without new_name are untouched."""
        df = pd.DataFrame({"col_a": [1, 2]})
        columns = [ColumnConfig(original_name="col_a")]

        result = rename_columns(df, columns)

        assert list(result.columns) == ["col_a"]

    def test_excluded_columns_already_absent_no_error(self):
        """Excluded columns (already absent from DataFrame) don't cause rename errors."""
        df = pd.DataFrame({"col_a": [1, 2]})
        columns = [
            ColumnConfig(original_name="col_excluded", excluded=True, new_name="should_not_appear"),
            ColumnConfig(original_name="col_a", new_name="alpha"),
        ]

        result = rename_columns(df, columns)

        assert "alpha" in result.columns
        assert "should_not_appear" not in result.columns

    def test_multiple_renames(self):
        """Multiple columns renamed in a single call."""
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        columns = [
            ColumnConfig(original_name="a", new_name="alpha"),
            ColumnConfig(original_name="b", new_name="beta"),
            ColumnConfig(original_name="c"),
        ]

        result = rename_columns(df, columns)

        assert sorted(result.columns.tolist()) == ["alpha", "beta", "c"]


class TestCastColumnTypes:
    """Unit tests for cast_column_types."""

    def test_cast_to_text(self):
        """CastType.TEXT: numeric column converted to string dtype."""
        df = pd.DataFrame({"num": [1, 2, 3]})
        columns = [ColumnConfig(original_name="num", cast_type=CastType.TEXT)]

        result = cast_column_types(df, columns)

        assert pd.api.types.is_string_dtype(result["num"]) or result["num"].dtype == object

    def test_cast_to_numeric(self):
        """CastType.NUMERIC: string column converted to numeric."""
        df = pd.DataFrame({"val": ["1.5", "2.0", "not_a_number"]})
        columns = [ColumnConfig(original_name="val", cast_type=CastType.NUMERIC)]

        result = cast_column_types(df, columns)

        assert pd.api.types.is_numeric_dtype(result["val"])
        # "not_a_number" should become NaN
        assert pd.isna(result["val"].iloc[2])

    def test_cast_to_boolean(self):
        """CastType.BOOLEAN: column cast to bool dtype."""
        df = pd.DataFrame({"flag": [1, 0, 1]})
        columns = [ColumnConfig(original_name="flag", cast_type=CastType.BOOLEAN)]

        result = cast_column_types(df, columns)

        assert result["flag"].dtype == bool

    def test_cast_to_date(self):
        """CastType.DATE: string column parsed to datetime."""
        df = pd.DataFrame({"dt": ["2024-01-01", "2024-06-15", "invalid"]})
        columns = [ColumnConfig(original_name="dt", cast_type=CastType.DATE)]

        result = cast_column_types(df, columns)

        assert pd.api.types.is_datetime64_any_dtype(result["dt"])
        # Invalid date → NaT
        assert pd.isna(result["dt"].iloc[2])

    def test_cast_type_none_leaves_column_unchanged(self):
        """cast_type=None: column dtype is not modified."""
        df = pd.DataFrame({"val": [1, 2, 3]})
        original_dtype = df["val"].dtype
        columns = [ColumnConfig(original_name="val")]

        result = cast_column_types(df, columns)

        assert result["val"].dtype == original_dtype

    def test_uses_effective_name_after_rename(self):
        """cast_column_types looks up by effective name (new_name if set)."""
        df = pd.DataFrame({"renamed_col": ["1", "2", "3"]})
        columns = [
            ColumnConfig(
                original_name="original_col", new_name="renamed_col", cast_type=CastType.NUMERIC
            )
        ]

        result = cast_column_types(df, columns)

        assert pd.api.types.is_numeric_dtype(result["renamed_col"])

    def test_excluded_column_skipped(self):
        """Excluded columns (cast_type set but excluded=True) are skipped."""
        df = pd.DataFrame({"col": ["1", "2"]})
        original_dtype = df["col"].dtype
        columns = [ColumnConfig(original_name="col", cast_type=CastType.NUMERIC, excluded=True)]

        result = cast_column_types(df, columns)

        assert result["col"].dtype == original_dtype


# ===========================================================================
# Tests for updated apply_transformations (rename + cast only)
# ===========================================================================


class TestApplyTransformations:
    def test_empty_config_returns_unchanged_data(self):
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})

        result = apply_transformations(df, IntegrityTransformation())

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert list(result.columns) == ["col1", "col2"]

    def test_backward_compat_columns_none(self):
        df = pd.DataFrame({"col1": [1, 2], "col2": ["x", "y"]})
        config = IntegrityTransformation(columns=None)

        result = apply_transformations(df, config)

        assert list(result.columns) == ["col1", "col2"]
        assert len(result) == 2

    def test_rename_applied_via_apply_transformations(self):
        """columns with new_name → rename applied."""
        df = pd.DataFrame({"original": [1, 2]})
        config = IntegrityTransformation(
            columns=[ColumnConfig(original_name="original", new_name="renamed")]
        )

        result = apply_transformations(df, config)

        assert "renamed" in result.columns
        assert "original" not in result.columns

    def test_cast_applied_via_apply_transformations(self):
        """columns with cast_type → cast applied."""
        df = pd.DataFrame({"num": ["1", "2", "3"]})
        config = IntegrityTransformation(
            columns=[ColumnConfig(original_name="num", cast_type=CastType.NUMERIC)]
        )

        result = apply_transformations(df, config)

        assert pd.api.types.is_numeric_dtype(result["num"])

    def test_excluded_columns_not_present_are_silently_ignored(self):
        """Excluded columns absent from DataFrame (SQL-level) → no KeyError."""
        # Simulates the state after read_data_from_postgis filtered out 'secret_col'
        df = pd.DataFrame({"visible_col": [1, 2]})
        config = IntegrityTransformation(
            columns=[
                ColumnConfig(original_name="secret_col", excluded=True),
                ColumnConfig(original_name="visible_col", new_name="shown"),
            ]
        )

        result = apply_transformations(df, config)

        assert "shown" in result.columns
        assert "secret_col" not in result.columns
        assert "visible_col" not in result.columns

    def test_projection_still_applied(self):
        """Projection logic preserved after refactor."""
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(
            {"name": ["A", "B"]}, geometry=[Point(0, 0), Point(1, 1)], crs="EPSG:4326"
        )
        config = IntegrityTransformation(force_projection=ForceProjection(type="EPSG:3857"))

        result = apply_transformations(gdf, config)

        assert isinstance(result, gpd.GeoDataFrame)
        assert result.crs.to_string() == "EPSG:3857"  # type: ignore[misc]

    def test_rename_then_cast_then_projection(self):
        """rename → cast → projection executed in correct order."""
        from shapely.geometry import Point

        gdf = gpd.GeoDataFrame(
            {"original": ["1", "2"], "name": ["A", "B"]},
            geometry=[Point(0, 0), Point(1, 1)],
            crs="EPSG:4326",
        )
        config = IntegrityTransformation(
            columns=[
                ColumnConfig(
                    original_name="original", new_name="renamed", cast_type=CastType.NUMERIC
                )
            ],
            force_projection=ForceProjection(type="EPSG:3857"),
        )

        result = apply_transformations(gdf, config)

        assert "renamed" in result.columns
        assert pd.api.types.is_numeric_dtype(result["renamed"])
        assert result.crs.to_string() == "EPSG:3857"  # type: ignore[misc]
