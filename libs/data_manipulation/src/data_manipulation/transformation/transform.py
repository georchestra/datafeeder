import logging
import re

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN
from data_manipulation.models import IntegrityTransformation
from data_manipulation.transformation.transform_columns import cast_column_types, rename_columns
from data_manipulation.transformation.transform_geom_point import create_geometries_from_columns
from data_manipulation.transformation.transform_projection import apply_projection

logger = logging.getLogger(__name__)

DEFAULT_CRS = "EPSG:4326"

_HEX_ONLY_RE = re.compile(r"^[0-9A-Fa-f]+$")


def _parse_geometry_series(series: pd.Series) -> np.ndarray:
    """Vectorised WKT/WKB-hex parsing using shapely 2's numpy-aware API.

    Format is detected once from the first non-null value: a string composed
    only of hex digits is treated as WKB-hex, otherwise WKT. Invalid values
    map to None (logged once with the count) instead of raising.
    """
    values = series.to_numpy(dtype=object, copy=False)
    mask_valid = pd.notna(values) & (values != "")

    if not mask_valid.any():
        return np.full(len(values), None, dtype=object)

    sample = next(v for v, ok in zip(values, mask_valid, strict=False) if ok)
    is_hex = isinstance(sample, str) and bool(_HEX_ONLY_RE.match(sample))

    result = np.full(len(values), None, dtype=object)
    candidates = values[mask_valid]
    try:
        if is_hex:
            parsed = shapely.from_wkb(candidates, on_invalid="ignore")
        else:
            parsed = shapely.from_wkt(candidates, on_invalid="ignore")
    except Exception as e:
        logger.warning(f"Failed to parse geometry column: {e}")
        return result

    result[mask_valid] = parsed
    invalid = pd.isna(pd.Series(parsed)).sum()
    if invalid:
        logger.warning(f"Failed to parse {int(invalid)} geometry value(s); set to None")
    return result


def _convert_geom_column_to_geodataframe(df: pd.DataFrame, projection: str) -> gpd.GeoDataFrame:
    """Convert DataFrame with 'geom' column to GeoDataFrame.

    Args:
        df: DataFrame with 'geom' column containing WKT or WKB geometries
        projection: CRS to apply to the GeoDataFrame

    Returns:
        GeoDataFrame with geometry column set
    """
    logger.info("Converting 'geom' column to geometry")
    try:
        geom_series: pd.Series = df[DEFAULT_GEOMETRY_COLUMN]  # type: ignore[assignment]
        geometries = _parse_geometry_series(geom_series)
        gdf = gpd.GeoDataFrame(df, geometry=geometries, crs=projection)  # type: ignore[no-any-return]
        return gdf
    except Exception as e:
        logger.error(f"Failed to convert 'geom' column to geometry: {e}")
        raise ValueError("i18nerror.transformation.geom_column_conversion_failed")


def _apply_projection_transformation(
    df: pd.DataFrame,
    projection: str,
    x_column: str | None = None,
    y_column: str | None = None,
) -> pd.DataFrame:
    """Apply projection/CRS transformation to geometries.

    Args:
        df: Input GeoDataFrame or DataFrame
        projection: Optional Target CRS/projection (e.g., 'EPSG:4326')
        x_column: Optional X/longitude column name for creating geometries
        y_column: Optional Y/latitude column name for creating geometries

    Returns:
        Transformed GeoDataFrame with projection applied
    """
    if y_column and x_column:
        # Create geometries from coordinate columns if specified
        # also apply projection
        logger.info(
            f"Creating geometries from columns {x_column}/{y_column} with projection {projection}"
        )
        try:
            df = create_geometries_from_columns(df, projection, x_column, y_column)
        except Exception:
            raise ValueError("i18nerror.transformation.geometry_creation_failed")

    elif y_column is None and x_column is not None or y_column is not None and x_column is None:
        raise ValueError("i18nerror.transformation.columns_both_required")

    elif isinstance(df, gpd.GeoDataFrame):
        # Apply projection to GeoDataFrame
        logger.info(f"Applying projection {projection} to GeoDataFrame")
        try:
            df = apply_projection(df, projection)
        except Exception:
            raise ValueError("i18nerror.transformation.projection_application_failed")

    return df


def apply_transformations(
    df: pd.DataFrame, transformation_config: IntegrityTransformation
) -> pd.DataFrame:
    """Apply transformations to a GeoDataFrame or a DataFrame.

    Args:
        df: Input GeoDataFrame or DataFrame
        transformation_config: IntegrityTransformation model containing:
            - columns: Optional list of column configurations
            - force_projection: Optional ForceProjection with type, x_column, y_column

    Returns:
        Transformed GeoDataFrame or DataFrame
    """
    logger.info(f"Applying transformations with config: {transformation_config}")

    # Rename and cast columns
    # Notes: filter and exclusion are handled upstream at the SQL level
    # (read_data_from_postgis with columns param), so excluded columns are
    # already absent from the DataFrame at this point.
    if transformation_config.columns:
        df = rename_columns(df, transformation_config.columns)
        df = cast_column_types(df, transformation_config.columns)

    # Handle projection/CRS transformation
    y_column = None
    x_column = None
    projection = None

    # Extract force_projection config
    force_projection = transformation_config.force_projection
    if force_projection:
        y_column = force_projection.y_column
        x_column = force_projection.x_column
        projection = force_projection.type

    # Convert projection to string if necessary
    if isinstance(projection, str):
        projection_str = projection
    else:
        # Priority: 1) Use specified projection, 2) Use existing GeoDataFrame CRS, 3) Default to EPSG:4326
        if projection is not None:
            projection_str = str(projection)
        if isinstance(df, gpd.GeoDataFrame) and df.crs is not None:
            projection_str = df.crs.to_string()
            logger.info(
                f"No projection specified, keeping existing GeoDataFrame CRS: {projection_str}"
            )
        else:
            projection_str = DEFAULT_CRS
            logger.info(f"No projection specified, defaulting to {DEFAULT_CRS}")

    logger.info(f"Projection set to {projection_str}")

    # Check if DataFrame has a 'geom' column and convert to GeoDataFrame
    if not isinstance(df, gpd.GeoDataFrame) and DEFAULT_GEOMETRY_COLUMN in df.columns:
        df = _convert_geom_column_to_geodataframe(df, projection_str)

    # Create geometries from columns if specified
    # and apply projection transformation
    df = _apply_projection_transformation(
        df,
        projection_str,
        x_column=x_column if isinstance(x_column, str) else None,
        y_column=y_column if isinstance(y_column, str) else None,
    )

    return df
