# Presentation

## Component architecture

```
datafeeder/
├── apps/
│   ├── backend/          # FastAPI REST API — ingestion orchestration & lifecycle
│   ├── frontend/         # Angular SPA — user interface
│   └── elt/              # Airflow DAGs — data processing pipelines
├── libs/
│   ├── data_manipulation/  # Shared Python lib — ingestion, transformation, GeoServer I/O
│   └── ai/                 # Shared Python lib — AI provider integrations
├── Makefile
└── docker-compose.yaml
```

- **Backend** (`apps/backend/`): FastAPI application, owns the `datafeeder` PostgreSQL schema, exposes the REST API
  consumed by the frontend and by Airflow (via webhook callbacks).
- **ELT** (`apps/elt/`): Airflow DAGs that do the actual data processing. No direct HTTP dependency on the backend at
  runtime — they share the database and call back to the backend through webhook URLs passed as DAG parameters.
- **Frontend** (`apps/frontend/`): Angular 20 SPA, talks exclusively to the backend REST API.
- **Shared library** (`libs/data_manipulation/`): imported by both the backend and the ELT DAGs — source-specific
  ingestion, the transformation pipeline, GeoServer write helpers, shared models.

## Dataset lifecycle

A dataset (an `IntegrityLink` record) goes through the following pipeline:

```
POST /staging        → creates IntegrityLink, triggers staging_dag (source → staging table)
                         success: records retrieve time
                         failure: deletes IntegrityLink + staging table

POST /process        → creates GN metadata record, triggers process_dag (staging → final table, with transformations)
                         success: publishes GeoServer layer, updates GN metadata record
                         failure: drops partial final table

(cron) ingestion_<uuid> → re-triggers process_dag on schedule (re-fetches from original source)

DELETE /integrity-link/{id} → unpublishes GeoServer layer, deletes GN record, drops tables, deletes row
```

Two DAGs implement the pipeline:

- **`staging_dag`**: ingests raw data from a source (FILE, URL, FTP, DATABASE, API/WFS/OGC) into a staging
  PostgreSQL table
- **`process_dag`**: applies transformations (column mapping, projection, filters) and writes to the final table;
  supports re-ingestion from source or reuse of an existing staging table

Both DAGs accept `success_callback_url` / `failure_callback_url` parameters and call them on completion, so the
backend can update the dataset's status asynchronously without polling Airflow.

## Minimal runtime

The minimum viable deployment requires:

- **Backend** + its PostgreSQL database
- **Airflow** with the ELT DAGs deployed

GeoServer and GeoNetwork complete the picture by publishing the layer and its metadata record.

The frontend is optional: the backend REST API is fully functional independently (see the interactive docs at
`/docs` on the backend's URL).
