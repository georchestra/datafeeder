# ELT (Airflow) configuration

The ELT DAGs (`staging_dag`, `process_dag`) run on Apache Airflow and share the same PostgreSQL database as the
backend. They have no direct HTTP dependency on the backend at startup: parameters (source configuration, transform
config, callback URLs) are passed in at trigger time, by the backend.

## Deploying the DAGs

The Docker Compose setup builds a custom Airflow image (`docker/Dockerfile.airflow`) that bundles `apps/elt/dags`
and the shared `libs/data_manipulation` package. For a platform deployment, deploy this image (or your own image
built the same way) as your Airflow workers/scheduler.

## Key settings

| Setting | Purpose |
|---|---|
| `AIRFLOW_UID` | User ID Airflow containers run as. Set in `.env`; `make install-python` writes your current UID automatically |
| `AIRFLOW_STAGING_TIMEOUT_SECONDS` | Timeout, in seconds, for the staging task execution (default: `600`) |
| `AIRFLOW_VERSION` | Base `apache/airflow` image tag used by `Dockerfile.airflow` (default: `3.1.8`) |

The backend also needs to be pointed at the Airflow instance: see `AIRFLOW_INTERNAL_URL`, `AIRFLOW_USERNAME` and
`AIRFLOW_PASSWORD` in the [backend configuration](backend.md).

## Callbacks

Both DAGs accept `success_callback_url` / `failure_callback_url` parameters and call them on completion. These URLs
point back at the backend (`BACKEND_INTERNAL_URL`), which is how the backend learns a run finished without polling
Airflow continuously.
