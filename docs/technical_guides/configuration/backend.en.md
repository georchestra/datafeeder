# Backend configuration

The backend reads its configuration from an env file, pointed to by the `DATAFEEDER_CONFIG` environment variable
(defaults to `<datadir>/datafeeder/datafeeder.env` when unset), falling back to defaults defined in
`src/core/config.py`. See `apps/backend/datafeeder.env` for a starting point.

## Precedence

Settings are resolved by `Settings.settings_customise_sources` in `src/core/config.py`. For a given setting, the
**first source below that provides a value wins** — sources further down are only used to fill in what's still
unset:

1. **geOrchestra `default.properties`** (`<datadir>/default.properties`) — flat `key=value` file managed by
   ops/deployment tooling. Matched by field name or by the geOrchestra-style aliases noted in the table below
   (e.g. `pgsqlHost` for `POSTGRES_DATAFEEDER_HOST`). Highest priority: if it sets a value, nothing else can
   override it.
2. **Environment variables** (real process/container env, including the same aliases, e.g. `POSTGRES_HOST`).
3. **This `.env` file** (`DATAFEEDER_CONFIG`, or `<datadir>/datafeeder/datafeeder.env` if unset).
4. **Init/keyword arguments** passed directly to `Settings(...)` in Python (mainly used in tests).
5. **Secret files** (pydantic-settings file-based secrets, e.g. Docker/Kubernetes secrets). Lowest priority; not
   currently wired up (no `secrets_dir` configured), so this source has no effect today.

Once a value is resolved, `${VAR}`-style references inside it are expanded against the process environment
(`expand_env_vars` validator), and any unset `POSTGRES_DATA_*` setting falls back to its `POSTGRES_DATAFEEDER_*`
counterpart.

## Key settings

| Setting | Purpose |
|---|---|
| `PROJECT_NAME` | Human readable name of the application |
| `ENVIRONMENT` | Deployment environment (`local`, `staging`, `production`); controls how strictly secrets are validated |
| `BACKEND_INTERNAL_URL` | Internal URL of the backend, as reachable by other services (server side) |
| `DATA_PUBLIC_URL` | Public base URL of the published data service (GeoServer), shown to users |
| `DATAHUB_PUBLIC_URL` | Public URL template of a dataset in Datahub, with `{metadata_id}` substituted |
| `METADATA_PUBLIC_URL` | Public base URL of the metadata catalog (GeoNetwork), shown to users |
| `DATADIR_PATH` | Path to the geOrchestra datadir used by the application |
| `POSTGRES_DATAFEEDER_HOST/PORT/USER/PASSWORD/DB` | Datafeeder's own database (the `datafeeder` schema: `IntegrityLink` records, schedules, etc.) |
| `POSTGRES_DATA_HOST/PORT/USER/PASSWORD/DB` | Database used for staging and final tables. Defaults to the same values as above if unset |
| `SOURCE_DATABASES` | JSON map of `{name: SQLAlchemy URI}` for the **Database** source type — see [adding a source database](source_database.md) |
| `USE_ORG_SCHEMA` | When `true`, final tables are written to a schema named after the org's short name instead of the shared `data` schema |
| `GEOSERVER_INTERNAL_URL` / `GEOSERVER_USER` / `GEOSERVER_PASSWORD` | GeoServer REST endpoint used for layer publication. URL MUST BE THROUGH THE GATEWAY in order to use authentication |
| `GEONETWORK_INTERNAL_URL` / `GEONETWORK_USERNAME` / `GEONETWORK_PASSWORD` | GeoNetwork endpoint used for metadata records URL MUST BE THROUGH THE GATEWAY in order to use authentication |
| `GEONETWORK_XSRF_TOKEN` | XSRF token sent to GeoNetwork (any UUID is accepted) |
| `GN_SYNC_MODE` | `ORG` or `ROLE` — which geOrchestra group flavor GeoNetwork groups are synced from |
| `METADATA_DEFAULT_GROUP_NAME` | Default GeoNetwork group name used when publishing metadata |
| `CONSOLE_INTERNAL_URL` | Internal URL of the geOrchestra console |
| `METADATA_GROUPS_LABEL_FILTER_REGEX` | Regex used to filter metadata groups shown in the authorization UI |
| `DATA_GROUPS_LABEL_FILTER_REGEX` | Regex used to filter data groups shown in the GeoServer authorization UI |
| `AIRFLOW_INTERNAL_URL` / `AIRFLOW_USERNAME` / `AIRFLOW_PASSWORD` | Airflow REST API used to trigger and monitor DAG runs |
| `TASK_EXECUTOR` | Task execution engine. Only `AIRFLOW` is supported today |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Lifetime of issued access tokens, in minutes |
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
