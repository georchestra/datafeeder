"""Unit tests for data_manipulation.type_detection."""

import pytest
import sqlalchemy.types as sqla_types

from data_manipulation.models import CastType
from data_manipulation.type_detection import detect_column_type_from_sqla


@pytest.mark.parametrize(
    "sqla_type, expected",
    [
        # Boolean
        (sqla_types.Boolean(), CastType.BOOLEAN),
        # Integer variants
        (sqla_types.Integer(), CastType.NUMERIC),
        (sqla_types.SmallInteger(), CastType.NUMERIC),
        (sqla_types.BigInteger(), CastType.NUMERIC),
        # Numeric / Float
        (sqla_types.Numeric(), CastType.NUMERIC),
        (sqla_types.Float(), CastType.NUMERIC),
        # Text / String
        (sqla_types.String(), CastType.TEXT),
        (sqla_types.Text(), CastType.TEXT),
        (sqla_types.VARCHAR(), CastType.TEXT),
        # Date / Datetime
        (sqla_types.Date(), CastType.DATE),
        (sqla_types.DateTime(), CastType.DATE),
        (sqla_types.Time(), CastType.DATE),
        # Geometry (custom / unknown type) falls back to TEXT
        (sqla_types.NullType(), CastType.TEXT),
    ],
)
def test_detect_column_type_from_sqla(sqla_type: object, expected: CastType) -> None:
    assert detect_column_type_from_sqla(sqla_type) == expected


def test_detect_column_type_from_sqla_boolean_not_numeric() -> None:
    """Boolean must not be classified as NUMERIC even though it's an Integer subclass."""
    assert detect_column_type_from_sqla(sqla_types.Boolean()) == CastType.BOOLEAN
