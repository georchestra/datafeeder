# data_manipulation

Shared Python library used by the Datafeeder backend and the Airflow ELT DAGs.

It centralizes the logic that reads, validates, transforms, and loads geospatial datasets so that the same code path is exercised whether a dataset is being previewed in the API or processed by a DAG.

## Layout

```
src/data_manipulation/
  ingestion.py        # Read a source (WFS, CSV, SHP, GeoJSON, …) into a (Geo)DataFrame
  transformation/     # Column rename / drop, type casting, filtering, reprojection
  type_detection.py   # Infer column types from raw data
  validators.py       # Schema and value validation
  database.py         # Helpers to load DataFrames into PostgreSQL / PostGIS
  geoserver.py        # GeoServer publication helpers
  encryption.py       # Secret handling for source credentials
  models.py           # Shared dataclasses / Pydantic models
  constants.py / utils.py / logging.py
```

## Install

The library is a uv workspace member; from the repository root:

```bash
uv sync --all-packages
```

It is then importable as `data_manipulation` from both the backend and the ELT DAGs.

The library source is bind-mounted into the Airflow containers, so edits are picked up live. If you change `pyproject.toml` dependencies, rebuild the Airflow images with `docker compose up -d --build`.

## Test

```bash
make test-libs
```
