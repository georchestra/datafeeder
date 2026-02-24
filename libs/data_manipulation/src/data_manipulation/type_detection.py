"""Utilities for detecting SQLAlchemy column types and mapping them to CastType."""

from typing import Any

import sqlalchemy.types as sqla_types

from data_manipulation.models import CastType


def detect_column_type_from_sqla(sqla_type: Any) -> CastType:
    """Map a SQLAlchemy column type to the closest :class:`CastType` value.

    Geometry and any unrecognised types default to :attr:`CastType.TEXT`.

    Args:
        sqla_type: A SQLAlchemy type instance (e.g. from ``table.columns[col].type``).

    Returns:
        The detected :class:`CastType`.
    """
    # Boolean must be checked before Integer because Boolean subclasses Integer
    # in some SQLAlchemy versions.
    if isinstance(sqla_type, sqla_types.Boolean):
        return CastType.BOOLEAN
    if isinstance(sqla_type, (sqla_types.Integer, sqla_types.Numeric, sqla_types.Float)):
        return CastType.NUMERIC
    if isinstance(sqla_type, (sqla_types.Date, sqla_types.DateTime, sqla_types.Time)):
        return CastType.DATE
    return CastType.TEXT
