import logging

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)


def create_geometries_from_columns(
    df: gpd.GeoDataFrame | pd.DataFrame,
    crs: str,
    x_column: str,
    y_column: str,
) -> gpd.GeoDataFrame | pd.DataFrame:
    """Create Point geometries from X/Y coordinate columns optimized for large datasets.

    Args:
        df: Input DataFrame
        x_column: X/longitude column name
        y_column: Y/latitude column name
        crs: Coordinate Reference System (default: EPSG:4326 for WGS84)
        batch_size: Size of batches for processing (auto-calculated if None)
        max_workers: Maximum threads for parallel processing (default: CPU count)

    Returns:
        GeoDataFrame with Point geometries created from coordinates
    """
    if not (x_column in df.columns and y_column in df.columns):
        raise ValueError(f"Columns {x_column} and/or {y_column} not found in data")

    # Check for non-numeric values in coordinate columns with tolerance
    tolerance = 0.8  # 80% of non-numeric values allowed
    x_numeric: pd.Series[float] = pd.to_numeric(df[x_column], errors="coerce")  # type: ignore[assignment]
    y_numeric: pd.Series[float] = pd.to_numeric(df[y_column], errors="coerce")  # type: ignore[assignment]
    x_nan_ratio = x_numeric.isna().mean()
    y_nan_ratio = y_numeric.isna().mean()

    if x_nan_ratio > tolerance or y_nan_ratio > tolerance:
        raise ValueError(
            f"Too many non-numeric values in columns: {x_column} ({x_nan_ratio:.1%}) - {y_column} ({y_nan_ratio:.1%})."
            f"Verify the data or consider preprocessing to clean the coordinate columns."
        )
    try:
        gdf = gpd.GeoDataFrame(
            df,
            geometry=gpd.points_from_xy(
                x_numeric,  # type: ignore[no-any-return]
                y_numeric,  # type: ignore[no-any-return]
            ),
            crs=crs,
        )
        logger.info(f"Created geometries from columns {x_column}/{y_column} and set CRS to {crs}")
        return gdf
    except Exception as e:
        logger.error(f"Failed to create geometries from columns {x_column}/{y_column}")
        raise e
