"""In-memory column transformation functions: rename and cast.

These functions operate on a DataFrame *after* it has been fetched from the
database.  Filter and exclusion are handled upstream at the SQL level
(see filter_sql.py / read_data_from_postgis), so excluded columns are already
absent from the DataFrame when these functions are called.
"""

import logging

import pandas as pd

from data_manipulation.models import CastType, ColumnConfig

logger = logging.getLogger(__name__)

# Common string representations of True/False, matched case-insensitively.
# Used by _parse_bool_from_strings to handle text-encoded boolean columns.
_BOOL_TRUE = frozenset({"true", "1", "yes", "on", "t", "y"})
_BOOL_FALSE = frozenset({"false", "0", "no", "off", "f", "n"})


def _parse_bool_from_strings(series: pd.Series) -> pd.Series:
    """Parse a string-typed Series to nullable boolean.

    pandas ``astype(bool)`` treats **any non-empty string** — including
    ``"False"``, ``"0"``, ``"no"`` — as ``True``, which is incorrect for
    user-visible column data.  This function maps common string
    representations to proper booleans and coerces unrecognised values to
    ``pd.NA`` (logged as a warning).

    Args:
        series: An object-dtype Series containing string boolean values.

    Returns:
        A Series with pandas nullable boolean dtype (``"boolean"``).
    """

    mapping: dict[str, bool] = {
        **dict.fromkeys(_BOOL_TRUE, True),
        **dict.fromkeys(_BOOL_FALSE, False),
    }
    normalised = series.astype("string").str.strip().str.lower()  # pyright: ignore[reportUnknownMemberType]
    result = normalised.map(mapping).astype("boolean")  # pyright: ignore[reportUnknownMemberType]
    na_count = int(result.isna().sum())
    if na_count > 0:
        logger.warning(f"Boolean cast: {na_count} value(s) could not be parsed and were set to NA")
    return result


def rename_columns(
    df: pd.DataFrame,
    columns: list[ColumnConfig],
) -> pd.DataFrame:
    """Rename columns in the DataFrame according to column configurations.

    Only renames non-excluded columns that have a non-None ``new_name``.
    Excluded columns are already absent from the DataFrame (filtered at the SQL
    level), so they are safely ignored here.

    Args:
        df: Input GeoDataFrame or DataFrame.
        columns: Column configurations containing rename instructions.

    Returns:
        DataFrame with columns renamed as configured.
    """
    rename_map: dict[str, str] = {
        col_config.original_name: col_config.new_name
        for col_config in columns
        if not col_config.excluded and col_config.new_name is not None
    }

    if not rename_map:
        return df

    logger.info(f"Renaming columns: {rename_map}")
    return df.rename(columns=rename_map)


def cast_column_types(
    df: pd.DataFrame,
    columns: list[ColumnConfig],
) -> pd.DataFrame:
    """Cast column types according to column configurations.

    Applied in-memory after the data is fetched.  Excluded columns are already
    absent from the DataFrame.  After a rename has been applied, columns are
    identified by their *effective* name (``new_name`` if set, else
    ``original_name``).

    Cast is optional for preview display (UI renders everything as strings)
    but required for the final write in the process DAG.

    Args:
        df: Input GeoDataFrame or DataFrame.
        columns: Column configurations containing cast instructions.

    Returns:
        DataFrame with columns cast to the specified types.
    """
    casts_to_apply = [c for c in columns if not c.excluded and c.cast_type is not None]
    if not casts_to_apply:
        return df

    df = df.copy()
    for col_config in casts_to_apply:
        # After rename the column lives under its effective name
        effective_name = (
            col_config.new_name if col_config.new_name is not None else col_config.original_name
        )

        if effective_name not in df.columns:
            logger.warning(
                f"Column '{effective_name}' not found in DataFrame, skipping cast to "
                f"{col_config.cast_type}"
            )
            continue

        cast_type = col_config.cast_type
        try:
            if cast_type == CastType.BOOLEAN:
                col = df[effective_name]
                # Use a custom string parser for object (text) columns so that
                # "False", "0", "no" correctly become False rather than True.
                # pandas astype(bool) treats any non-empty string as True.
                if col.dtype == object:
                    df[effective_name] = _parse_bool_from_strings(col)  # type: ignore[arg-type]
                else:
                    df[effective_name] = col.astype(bool)  # type: ignore[union-attr]
            elif cast_type == CastType.NUMERIC:
                # Pin dtype to float64 so the preview path matches the SQL path
                # (transform_sql._cast_expr emits double precision unconditionally).
                df[effective_name] = pd.to_numeric(  # pyright: ignore[reportUnknownMemberType]
                    df[effective_name], errors="coerce"
                ).astype("float64")  # pyright: ignore[reportAttributeAccessIssue]
            elif cast_type == CastType.TEXT:
                df[effective_name] = df[effective_name].astype(str)  # pyright: ignore[reportUnknownMemberType]
            elif cast_type == CastType.DATE:
                df[effective_name] = pd.to_datetime(df[effective_name], errors="coerce")  # type: ignore[arg-type]
            logger.info(f"Cast column '{effective_name}' to {cast_type}")
        except Exception as e:
            logger.warning(f"Failed to cast column '{effective_name}' to {cast_type}: {e}")

    return df
