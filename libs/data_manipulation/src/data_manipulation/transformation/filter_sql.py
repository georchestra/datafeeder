"""SQL-level column filtering.

Filters are expressed as SQLAlchemy bound-parameter expressions so user values
are always passed as SQL parameters (no injection risk) and ILIKE special
characters are escaped to match literally.
"""

import logging
from typing import Any

from sqlalchemy import ColumnElement, Text, cast

from data_manipulation.models import ColumnFilter, FilterOperator

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
