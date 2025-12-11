from data_manipulation.ingestion import (
    ingest_data_from_file_into_postgis,
    ingest_data_from_url_into_postgis,
    read_data_from_postgis,
    apply_transformations,
    write_data_to_postgis,
)

__all__ = [
    "hello",
    "ingest_data_from_file_into_postgis",
    "ingest_data_from_url_into_postgis",
    "read_data_from_postgis",
    "apply_transformations",
    "write_data_to_postgis",
]


def hello() -> str:
    return "Hello from data_manipulation!"
