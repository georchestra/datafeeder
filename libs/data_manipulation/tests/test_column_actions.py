"""Tests for SQL-level column operations (selection and filtering)."""

from sqlalchemy import Column, MetaData, Table, Text
from sqlalchemy.dialects import postgresql

from data_manipulation.models import ColumnConfig, ColumnFilter, FilterOperator
from data_manipulation.transformation.filter_sql import (
    _escape_like,  # type: ignore[reportPrivateUsage]
    build_filter_clause,
    build_sql_column_ops,
)


def _table() -> Table:
    metadata = MetaData(schema="staging")
    return Table(
        "places",
        metadata,
        Column("name", Text),
        Column("city", Text),
        Column("secret", Text),
    )


def _compile(clause: object) -> str:
    return str(clause.compile(dialect=postgresql.dialect()))  # type: ignore[attr-defined]


class TestEscapeLike:
    def test_escapes_percent(self) -> None:
        assert _escape_like("50%") == "50\\%"

    def test_escapes_underscore(self) -> None:
        assert _escape_like("a_b") == "a\\_b"

    def test_escapes_backslash_first(self) -> None:
        assert _escape_like("a\\b") == "a\\\\b"


class TestBuildFilterClause:
    def test_exactly_uses_plain_pattern(self) -> None:
        col = _table().c["name"]
        clause = build_filter_clause(
            col, ColumnFilter(operator=FilterOperator.EXACTLY, value="paris")
        )
        sql = _compile(clause).upper()
        assert "ILIKE" in sql

    def test_contains_wraps_with_percent(self) -> None:
        col = _table().c["name"]
        clause = build_filter_clause(
            col, ColumnFilter(operator=FilterOperator.CONTAINS, value="par")
        )
        # The bound value should be %par% — inspect the bound parameters
        params = clause.compile(dialect=postgresql.dialect()).params  # type: ignore[attr-defined]
        assert any(v == "%par%" for v in params.values())

    def test_starts_with_appends_percent(self) -> None:
        col = _table().c["name"]
        clause = build_filter_clause(
            col, ColumnFilter(operator=FilterOperator.STARTS_WITH, value="par")
        )
        params = clause.compile(dialect=postgresql.dialect()).params  # type: ignore[attr-defined]
        assert any(v == "par%" for v in params.values())

    def test_value_is_escaped_in_bound_param(self) -> None:
        col = _table().c["name"]
        clause = build_filter_clause(
            col, ColumnFilter(operator=FilterOperator.CONTAINS, value="50%")
        )
        params = clause.compile(dialect=postgresql.dialect()).params  # type: ignore[attr-defined]
        assert any("50\\%" in str(v) for v in params.values())


class TestBuildSqlColumnOps:
    def test_empty_columns_returns_all(self) -> None:
        table = _table()
        select_cols, where_clauses = build_sql_column_ops([], table)
        assert len(select_cols) == len(table.c)
        assert where_clauses == []

    def test_excluded_column_omitted(self) -> None:
        table = _table()
        select_cols, _ = build_sql_column_ops(
            [
                ColumnConfig(original_name="name"),
                ColumnConfig(original_name="secret", excluded=True),
            ],
            table,
        )
        names = [c.name for c in select_cols]
        assert "name" in names
        assert "secret" not in names

    def test_unknown_column_skipped(self) -> None:
        table = _table()
        select_cols, _ = build_sql_column_ops([ColumnConfig(original_name="does_not_exist")], table)
        assert select_cols == []

    def test_filter_produces_where_clause(self) -> None:
        table = _table()
        _, where_clauses = build_sql_column_ops(
            [
                ColumnConfig(
                    original_name="city",
                    filter=ColumnFilter(operator=FilterOperator.EXACTLY, value="paris"),
                )
            ],
            table,
        )
        assert len(where_clauses) == 1
