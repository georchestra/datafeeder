import logging

import geopandas as gpd
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def apply_encoding(
    df: gpd.GeoDataFrame | pd.DataFrame, encoding: str
) -> gpd.GeoDataFrame | pd.DataFrame:
    """Apply encoding transformation to text columns.

    Re-encodes text by treating it as latin-1 bytes and decoding with the specified encoding.
    """
    try:
        text_columns = df.select_dtypes(include=["object"]).columns

        if len(text_columns) > 0:
            for col in text_columns:
                try:
                    values = df[col].values
                    mask = np.array([isinstance(x, str) for x in values])

                    if mask.any():
                        string_values = values[mask]

                        # Apply the requested encoding transformation
                        # assuming source is utf-8 because it has been read as such with pandas
                        encoded = [
                            v.encode("utf-8", errors="ignore").decode(encoding, errors="replace")
                            for v in string_values
                        ]

                        values[mask] = encoded
                        df[col] = values

                except Exception as e:
                    logger.warning(f"Failed to apply encoding to column {col}: {e}")

            logger.info(f"Applied encoding {encoding} to {len(text_columns)} columns")

    except Exception as e:
        logger.warning(f"Failed to apply encoding: {e}")

    return df
