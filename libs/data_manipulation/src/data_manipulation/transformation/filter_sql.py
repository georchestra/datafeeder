"""SQL-level column operations: selection and filtering.

Filter and exclusion are handled at the SQL level so that:
- WHERE clauses apply before LIMIT (correct row count after filter)
- Excluded columns are never fetched from the database
- User filter values are always bound as SQL parameters (no injection risk)
"""

import logging
from typing import Any

from sqlalchemy import Column, ColumnElement, Table, Text, cast

from data_manipulation.models import ColumnConfig, FilterOperator

logger = logging.getLogger(__name__)

_LIKE_ESCAPE_CHAR = "\\"


def _escape_like(value: str) -> str:
    """Escape LIKE wildcard characters in a user-provided value.

    Escapes the escape character itself first, then % and _, so that
    the value is treated as a plain text match in a LIKE expression.
    """
    value = value.replace(_LIKE_ESCAPE_CHAR, _LIKE_ESCAPE_CHAR * 2)
    value = value.replace("%", f"{_LIKE_ESCAPE_CHAR}%")
    value = value.replace("_", f"{_LIKE_ESCAPE_CHAR}_")
    return value


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
            # Cast to TEXT for uniform comparison regardless of native column type.
            # SQLAlchemy's == and .like() automatically bind the value as a parameter,
            # so no user input is ever interpolated into the SQL text.
            #
            # Case-sensitivity note (by design):
            #   EXACTLY   → == comparison   → CASE-SENSITIVE after TEXT cast
            #   CONTAINS  → ilike()         → CASE-INSENSITIVE (PostgreSQL ILIKE)
            #   STARTS_WITH → ilike()       → CASE-INSENSITIVE (PostgreSQL ILIKE)
            # This inconsistency is intentional: exact matching is strict by nature,
            # while substring/prefix matching is more useful case-insensitively.
            col_as_text = cast(col, Text)
            filter_value = col_config.filter.value
            operator = col_config.filter.operator

            if operator == FilterOperator.EXACTLY:
                where_clauses.append(col_as_text == filter_value)
            elif operator == FilterOperator.CONTAINS:
                escaped = _escape_like(filter_value)
                where_clauses.append(col_as_text.like(f"%{escaped}%", escape=_LIKE_ESCAPE_CHAR))
            elif operator == FilterOperator.STARTS_WITH:
                escaped = _escape_like(filter_value)
                where_clauses.append(col_as_text.like(f"{escaped}%", escape=_LIKE_ESCAPE_CHAR))

    return select_cols, where_clauses
