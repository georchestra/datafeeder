# Backend configuration

The backend reads its configuration from an env file, pointed to by the `DATAFEEDER_CONFIG` environment variable
(defaults to `<datadir>/datafeeder-python/datafeeder.env` when unset), falling back to defaults defined in
`src/core/config.py`. See `apps/backend/.env.example` for a starting point.

## Key settings

| Setting | Purpose |
|---|---|
| `POSTGRES_DATAFEEDER_HOST/PORT/USER/PASSWORD/DB` | Datafeeder's own database (the `datafeeder` schema: `IntegrityLink` records, schedules, etc.) |
| `POSTGRES_DATA_HOST/PORT/USER/PASSWORD/DB` | Database used for staging and final tables. Defaults to the same values as above if unset |
| `SOURCE_DATABASES` | JSON map of `{name: SQLAlchemy URI}` for the **Database** source type |
| `USE_ORG_SCHEMA` | When `true`, final tables are written to a schema named after the org's short name instead of the shared `data` schema |
| `GEOSERVER_INTERNAL_URL` / `GEOSERVER_USER` / `GEOSERVER_PASSWORD` | GeoServer REST endpoint used for layer publication |
| `GEONETWORK_INTERNAL_URL` / `GEONETWORK_USERNAME` / `GEONETWORK_PASSWORD` | GeoNetwork endpoint used for metadata records |
| `GN_SYNC_MODE` | `ORG` or `ROLE` — which geOrchestra group flavor GeoNetwork groups are synced from |
| `AIRFLOW_INTERNAL_URL` / `AIRFLOW_USERNAME` / `AIRFLOW_PASSWORD` | Airflow REST API used to trigger and monitor DAG runs |
| `TASK_EXECUTOR` | Task execution engine. Only `AIRFLOW` is supported today |
| `ENCRYPTION_KEY` | Encrypts sensitive data at rest (e.g. HTTP Basic Auth credentials for FTP/URL sources) |
| `SECRET_KEY` | Signs internal auth tokens used between the backend and Airflow callbacks |
| `PROJECTIONS` | JSON list of `{value, label}` projections offered to users in the transformation step |
| `TMP_UPLOAD_PATH` | Local scratch directory used while a file upload is being staged |
| `BACKEND_CORS_ORIGINS` / `FRONTEND_HOST` | CORS configuration for the frontend origin(s) |
| `RECURRENCE_EXECUTION_HOUR` | Hour of day (0-23) at which daily/weekly/monthly/yearly recurring imports run |

!!! note "Secrets"

    `SECRET_KEY`, `POSTGRES_DATAFEEDER_PASSWORD` and `ENCRYPTION_KEY` must not be left at their default/placeholder
    value outside of `local` environment: the backend refuses to start otherwise.

## Database migrations

The backend owns its schema through Alembic. On `make run-backend`, migrations are applied automatically
(`uv run alembic upgrade head`) before starting the API server.
