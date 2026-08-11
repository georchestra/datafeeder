# Developing without Airflow: the local task executor

Running the full Airflow stack (redis, api-server, scheduler, dag-processor, worker, triggerer) is not always
necessary to work on the datafeeder: staging and process are, in the end, plain Python calls into
`libs/data_manipulation/`. The `LOCAL` task executor runs that logic directly inside the backend process, so a
dev loop can be just `make up`, `make run-backend`, `npm start` — no Airflow containers involved.

This complements the [`BaseTaskExecutor` abstraction](architecture.md#design-principles): `AirflowTaskExecutor`
(`apps/backend/src/services/executors/airflow_executor.py`) and `LocalTaskExecutor`
(`apps/backend/src/services/executors/local_executor.py`) implement the same interface, and routes never talk to
Airflow directly (with one documented exception below).

## Enabling it

In `apps/backend/datafeeder.env`:

```bash
TASK_EXECUTOR=LOCAL
BACKEND_INTERNAL_URL=http://localhost:8000
```

`BACKEND_INTERNAL_URL` matters: with `AIRFLOW`, DAGs run inside Docker and need `host.docker.internal` to reach
the host-run backend. With `LOCAL`, ingestion runs in the backend's own process on the host, so it must be
`localhost` — using the Docker-only hostname here fails with a DNS resolution error.

`make up` no longer starts Airflow (the 7 Airflow services are behind the `airflow` Compose profile). Use
`make up-airflow` when you actually need to test against real Airflow.

Restart `make run-backend` after changing `datafeeder.env` — settings are cached at startup and `--reload` only
watches source directories, not this file.

## What it actually runs

`LocalTaskExecutor` only covers the flows the backend itself triggers:

- **Staging** (`trigger_staging_task`): same `match source_type` dispatch as
  `apps/elt/dags/task_groups/ingestion.py`, calling `data_manipulation.ingestion.*` directly.
- **Process, direct mode** (`trigger_process_task`): same chunked read/transform/write loop as
  `apps/elt/dags/task_groups/transformation.py`, using an existing staging table.

Each call runs in a background thread and reports status through the same endpoints the frontend already polls
(`GET /airflow/dags/{dag_id}/runs/{run_id}/status`), and calls the same `success_callback_url`/
`failure_callback_url` the backend builds for Airflow — just via a direct `requests.post` to itself instead of a
DAG calling back.

## Limitations

- **No worker pool.** There's a single `ThreadPoolExecutor(max_workers=4)` living inside the backend process —
  no Celery, no distributed workers, no queueing beyond those 4 slots. A 5th concurrent run just waits for a
  slot. Run state is an in-memory dict: it is lost whenever the backend process restarts (including
  `uvicorn --reload` picking up a code change), and there's no persistence or retry across restarts.
- **No recurrence.** Scheduled/recurring re-ingestion (`apps/elt/dags/process-dag-generator.py`, the "refresh
  from source" mode of `process_dag`) has no local equivalent — it fundamentally needs a real scheduler. This is
  an Airflow-only feature; don't rely on schedules while testing with `TASK_EXECUTOR=LOCAL`.
- **No real logs.** `get_task_logs` only returns the last exception message + traceback for a failed run, kept
  in memory — there's no structured, persistent task log like Airflow's. `GET /airflow/dags/{dag_id}/runs/{intlink_id}`
  (DAG run history, used by the events page and the metadata status badge) also always returns an empty result
  under `LOCAL`, since it bypasses `BaseTaskExecutor` and talks to the Airflow API directly — there is no run
  history to show.
- **No timeout.** Airflow's `dagrun_timeout` / `"timed_out"` note mechanism isn't reproduced; `get_task_note`
  always returns `None`. A stuck ingestion (e.g. a source that hangs) will just occupy a thread pool slot
  indefinitely.

None of this matters for the day-to-day loop of importing a file, mapping columns, and checking the published
layer — which is what `LOCAL` is for. Reach for `make up-airflow` (`TASK_EXECUTOR=AIRFLOW`) as soon as you need
to test recurrence, real task logs, or anything involving the scheduler.
