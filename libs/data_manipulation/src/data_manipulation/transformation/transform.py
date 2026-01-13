import logging

import geopandas as gpd
import pandas as pd

from data_manipulation.transformation.transform_encoding import apply_encoding
from data_manipulation.transformation.transform_geom_point import create_geometries_from_columns
from data_manipulation.transformation.transform_projection import apply_projection

logger = logging.getLogger(__name__)

DEFAULT_CRS = "EPSG:4326"


def _apply_projection_transformation(
    df: gpd.GeoDataFrame | pd.DataFrame,
    projection: str,
    x_column: str | None = None,
    y_column: str | None = None,
) -> gpd.GeoDataFrame | pd.DataFrame:
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
    df: gpd.GeoDataFrame | pd.DataFrame, transformation_config: dict[str, str | object | None]
) -> gpd.GeoDataFrame | pd.DataFrame:
    """Apply transformations to a GeoDataFrame or a DataFrame.

    Args:
        data: Input GeoDataFrame or DataFrame
        transformation_config: JSON configuration for transformations

    Returns:
        Transformed GeoDataFrame or DataFrame
    """
    logger.info(f"Applying transformations with config: {transformation_config}")

    encoding = transformation_config.get("encoding")
    y_column = transformation_config.get("y_column")
    x_column = transformation_config.get("x_column")
    projection = transformation_config.get("projection")

    # Convert projection to string if necessary
    if isinstance(projection, str):
        projection_str = projection
    else:
        projection_str = str(projection) if projection is not None else DEFAULT_CRS
        logger.info(f"Default projection set to {projection_str}")

    # Apply encoding transformation if specified
    if encoding and isinstance(encoding, str):
        df = apply_encoding(df, encoding)

    # Apply projection transformation if specified
    df = _apply_projection_transformation(
        df,
        projection_str,
        x_column=x_column if isinstance(x_column, str) else None,
        y_column=y_column if isinstance(y_column, str) else None,
    )

    return df
