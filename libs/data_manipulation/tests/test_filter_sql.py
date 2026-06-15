"""Unit tests for build_filter_clause (no DB required)."""

from typing import Any

from sqlalchemy import BinaryExpression, Column, Integer, MetaData, String, Table
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import Cast

from data_manipulation.models import ColumnFilter, FilterOperator
from data_manipulation.transformation.filter_sql import (
    _escape_like,  # pyright: ignore[reportPrivateUsage]
    build_filter_clause,
)

_PG = postgresql.dialect()


def _make_table() -> Table:
    metadata = MetaData()
    return Table(
        "test_table",
        metadata,
        Column("id", Integer),
        Column("name", String),
        Column("city", String),
    )


def _filter(value: str, operator: FilterOperator) -> BinaryExpression[Any]:
    table = _make_table()
    clause = build_filter_clause(
        table.c.name, ColumnFilter(operator=operator, value=value)
    )
    assert isinstance(clause, BinaryExpression)
    return clause


# ---------------------------------------------------------------------------
# Escaping
# ---------------------------------------------------------------------------


def test_escape_like_escapes_percent() -> None:
    assert _escape_like("50%") == "50\\%"


def test_escape_like_escapes_underscore() -> None:
    assert _escape_like("a_b") == "a\\_b"


def test_escape_like_escapes_backslash_first() -> None:
    # The backslash must be doubled before %/_ are escaped, otherwise the
    # escape characters introduced for %/_ would themselves get doubled.
    assert _escape_like("a\\b") == "a\\\\b"
    assert _escape_like("\\%") == "\\\\\\%"


# ---------------------------------------------------------------------------
# Operator pattern shapes
# ---------------------------------------------------------------------------


def test_exactly_casts_to_text_and_uses_ilike() -> None:
    expr = _filter("Alice", FilterOperator.EXACTLY)
    # The left operand is a CAST(... AS TEXT).
    assert isinstance(expr.left, Cast)
    compiled = expr.compile(dialect=_PG, compile_kwargs={"literal_binds": True})
    assert "ILIKE" in str(compiled).upper()


def test_contains_wraps_value_with_percent() -> None:
    expr = _filter("Par", FilterOperator.CONTAINS)
    compiled = str(expr.compile(compile_kwargs={"literal_binds": True}))
    assert "%Par%" in compiled


def test_starts_with_appends_percent() -> None:
    expr = _filter("Al", FilterOperator.STARTS_WITH)
    compiled = str(expr.compile(compile_kwargs={"literal_binds": True}))
    assert "Al%" in compiled


# ---------------------------------------------------------------------------
# Bound-parameter safety
# ---------------------------------------------------------------------------


def test_exactly_value_stays_bound_parameter() -> None:
    value = "SuperSecretValue"
    expr = _filter(value, FilterOperator.EXACTLY)
    compiled = str(expr.compile(compile_kwargs={"literal_binds": False}))
    assert value not in compiled, f"value was inlined in SQL text: {compiled}"


def test_contains_value_stays_bound_parameter() -> None:
    value = "InjectionAttempt"
    expr = _filter(value, FilterOperator.CONTAINS)
    compiled = str(expr.compile(compile_kwargs={"literal_binds": False}))
    assert value not in compiled
