# Datafeeder e2e tests

Playwright tests running against a local instance on `localhost:8080`.

## Setup

```bash
uv sync
uv run playwright install chromium
cp .env.example .env  # fill in real FTP / basic-auth credentials
```

## Run

```bash
uv run pytest                          # all tests, headed
uv run pytest tests/test_import.py     # one file
uv run pytest -k parquet               # one case by id
uv run pytest --headed=false           # headless
```

## Generate with playwright

```bash
uv run playwright codegen http://localhost:8080
```

## Worker memory

Watch the airflow-worker container's memory usage while a test run triggers an import:

```bash
./watch-worker-mem.sh [container] [interval_seconds]  # defaults: datafeeder-airflow-worker-1, 2
```
