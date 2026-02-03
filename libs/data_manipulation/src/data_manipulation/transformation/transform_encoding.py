import logging

import geopandas as gpd
import pandas as pd

logger = logging.getLogger(__name__)


def apply_encoding(
    df: gpd.GeoDataFrame | pd.DataFrame, encoding: str
) -> gpd.GeoDataFrame | pd.DataFrame:
    """Apply encoding transformation to text columns."""
    try:
        text_columns = df.select_dtypes(include=["object"]).columns

        if len(text_columns) > 0:
            # Define encoding function to apply
            def encode_cell(v: object) -> object:
                if isinstance(v, str):
                    return v.encode("utf-8", errors="ignore").decode(encoding, errors="replace")
                return v

            # Apply encoding to all text columns at once using map (DataFrame-wide operation)
            df[text_columns] = df[text_columns].map(encode_cell)
            logger.info(f"Applied encoding {encoding} to {len(text_columns)} columns")

    except Exception as e:
        logger.warning(f"Failed to apply encoding: {e}")

    return df
