import logging

import geopandas as gpd

logger = logging.getLogger(__name__)


def apply_projection(
    gdf: gpd.GeoDataFrame,
    projection: str,
) -> gpd.GeoDataFrame:
    """Apply CRS/projection to existing geometries in a GeoDataFrame.

    Args:
        gdf: Input GeoDataFrame with geometries
        projection: Target CRS/projection (e.g., 'EPSG:4326')

    Returns:
        GeoDataFrame with projection applied
    """
    try:
        logger.info(f"Applying projection {projection} to geometries")
        gdf.set_crs(projection, inplace=True, allow_override=True)
    except Exception as e:
        logger.warning(f"Failed to set CRS to {projection}: {e}")
        raise e

    return gdf
