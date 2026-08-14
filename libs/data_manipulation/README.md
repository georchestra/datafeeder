# data_manipulation

Shared Python library used by the Datafeeder backend and the Airflow ELT DAGs.

It centralizes the logic that ingests, validates, transforms, and publishes geospatial datasets so that the same code path is exercised whether a dataset is being previewed in the API or processed by a DAG.

Data is streamed **directly into PostGIS** with `ogr2ogr` (GDAL) and every transformation (rename, cast, reproject, geometry build, filter) is expressed as **parameterized SQL** executed server-side. Datasets never leave the database except for a small bounded preview — there is no in-memory geopandas/pandas layer.

## Layout

```
src/data_manipulation/
  ingestion.py            # Stream a source (WFS/OAPIF, CSV, SHP, GeoJSON, Parquet, DB, …) into PostGIS via ogr2ogr
  transformation/
    sql_transform.py      # Build the canonical SQL SELECT; CTAS to final table + bounded preview
    filter_sql.py         # SQL column selection / ILIKE filters
  type_detection.py       # Infer column types from the database schema
  validators.py           # Schema and value validation
  database.py             # PostgreSQL / PostGIS helpers
  geoserver.py            # GeoServer publication helpers
  encryption.py           # Secret handling for source credentials
  models.py               # Shared dataclasses / Pydantic models
  constants.py / utils.py / logging.py
```

## Requirements

Ingestion shells out to `ogr2ogr`, so the runtime image must ship **GDAL** (with the
Parquet/Arrow driver for `.parquet`/`.geoparquet` support — GDAL ≥ 3.5). The Airflow and
backend Docker images provide it; it is not required to import the library or run the unit
tests (which mock the `ogr2ogr` subprocess).

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
