# Datafeeder ELT

Apache Airflow 3.x DAGs that perform the actual extraction, loading, and transformation of datasets handed off by the backend.

## Layout

```
dags/
  staging_dag.py            # Ingest a dataset into a staging table
  process_dag.py            # Transform staging data into the final table
  process-dag-generator.py  # Dynamically generates recurrence DAGs from integrity_link rows
  callback.py               # Backend callback helpers (success / failure)
  task_groups/              # Reusable Airflow TaskGroups
  models.py / utils.py      # Shared types and helpers
  tests/                    # DAG-level tests
```

## Run

DAGs are executed by Airflow inside Docker Compose:

```bash
make up-light            # Airflow + gateway + LDAP
# or
make up-full             # full stack with backend, frontend, GeoServer, GeoNetwork
make reload-airflow-deps # rebuild data_manipulation inside Airflow images
```

Airflow is then reachable at:

- http://localhost:8080/airflow (through the gateway)
- http://localhost:8081 (direct, with API docs at `/docs`)
- Credentials: `airflow / airflow`

## DAG flow (summary)

1. The backend triggers `staging_dag` with a `dag_run_id`, source type, source URL, and success/failure callback URLs.
2. `staging_dag` downloads, parses, and loads the dataset into a PostgreSQL staging table, then calls back the backend.
3. After user-driven configuration, the backend triggers `process_dag` to transform staging data into the final table and update the linked GeoServer layer / GeoNetwork record.
4. For recurrent ingestions, `process-dag-generator.py` polls `integrity_link` rows with `schedule_enabled = true` and dynamically materializes scheduled DAGs.

See [`ARCHITECTURE.md`](../../ARCHITECTURE.md) for the full pipeline overview.

## Test

```bash
uv run pytest apps/elt/dags/tests
```
