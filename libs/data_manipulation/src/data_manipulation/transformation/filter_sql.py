"""SQL-level column operations: selection and filtering.

Filter and exclusion are handled at the SQL level so that:
- WHERE clauses apply before LIMIT (correct row count after filter)
- Excluded columns are never fetched from the database
- User filter values are always bound as SQL parameters (no injection risk)
"""

import logging
from typing import Any

from sqlalchemy import Column, ColumnElement, Table, Text, cast

from data_manipulation.models import ColumnConfig, ColumnFilter, FilterOperator

logger = logging.getLogger(__name__)

_LIKE_ESCAPE_CHAR = "\\"


def _escape_like(value: str) -> str:
    """Escape special ILIKE characters in a user-provided value.

    ILIKE treats '%', '_', and the escape character '\\' as special.
    This function escapes all three so the value is matched literally.
    The escape character must be processed first to avoid double-escaping.
    """
    value = value.replace(_LIKE_ESCAPE_CHAR, _LIKE_ESCAPE_CHAR * 2)
    value = value.replace("%", f"{_LIKE_ESCAPE_CHAR}%")
    value = value.replace("_", f"{_LIKE_ESCAPE_CHAR}_")
    return value


def build_filter_clause(col: ColumnElement[Any], column_filter: ColumnFilter) -> ColumnElement[Any]:
    """Build a single case-insensitive ILIKE WHERE clause for a column.

    The column is cast to TEXT so all types (int, date, etc.) are compared
    uniformly. The filter value is escaped so '%', '_', and '\\' are treated as
    literal characters, and is always passed as a bound parameter (no SQL
    injection risk).

    Pattern shapes:
        EXACTLY     -> "value"    — full string must match
        CONTAINS    -> "%value%"  — value can appear anywhere
        STARTS_WITH -> "value%"   — string must begin with value
    """
    col_as_text = cast(col, Text)
    escaped = _escape_like(column_filter.value)
    operator = column_filter.operator

    if operator == FilterOperator.EXACTLY:
        return col_as_text.ilike(escaped, escape=_LIKE_ESCAPE_CHAR)
    if operator == FilterOperator.CONTAINS:
        return col_as_text.ilike(f"%{escaped}%", escape=_LIKE_ESCAPE_CHAR)
    # STARTS_WITH
    return col_as_text.ilike(f"{escaped}%", escape=_LIKE_ESCAPE_CHAR)


def build_sql_column_ops(
    columns: list[ColumnConfig],
    table: Table,
) -> tuple[list[Column[Any]], list[ColumnElement[Any]]]:
    """Build SQL SELECT column list and WHERE clauses from column configurations.

    Excluded columns are omitted from the SELECT entirely.
    Active filters are expressed as SQLAlchemy bound-parameter expressions
    (`.like()` / `==`) — user values are never interpolated into raw SQL text.

    Args:
        columns: List of column configurations.
        table: SQLAlchemy Table object (metadata must already be loaded).

    Returns:
        Tuple of (select_cols, where_clauses) where:
        - select_cols: ordered list of Column objects to include in SELECT
        - where_clauses: list of ColumnElement conditions for the WHERE clause
    """
    if not columns:
        # Return all columns and no filters when list is empty
        return list(table.c), []

    select_cols: list[Column[Any]] = []
    where_clauses: list[ColumnElement[Any]] = []

    for col_config in columns:
        if col_config.excluded:
            # Excluded columns are omitted from the SELECT — their filter is also skipped
            continue

        col_name = col_config.original_name
        if col_name not in table.c:
            logger.warning(f"Column '{col_name}' not found in table '{table.name}', skipping")
            continue

        col = table.c[col_name]
        select_cols.append(col)

        if col_config.filter is not None:
            where_clauses.append(build_filter_clause(col, col_config.filter))

    return select_cols, where_clauses
