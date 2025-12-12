import geopandas as gpd
from sqlalchemy.engine import Engine


def ingest_data_from_file_into_postgis(
    file_path: str, table_name: str, engine: Engine, schema: str | None = None
) -> None:
    """Ingest data from a file into a PostGIS table."""

    try:
        gdf = gpd.read_file(file_path)
        gdf.to_postgis(table_name, engine, if_exists="replace", schema=schema)
    except Exception as e:
        print(f"Error ingesting data from file {file_path}: {e}")
        raise


def ingest_data_from_url_into_postgis(
    url: str, table_name: str, engine: Engine, schema: str | None = None
) -> None:
    """Ingest data from a URL into a PostGIS table."""

    try:
        gdf = gpd.read_file(url)
        gdf.to_postgis(table_name, engine, if_exists="replace", schema=schema)
    except Exception as e:
        print(f"Error ingesting data from URL {url}: {e}")
        raise
