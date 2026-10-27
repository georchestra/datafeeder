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
uv run pytest                                                      # all tests, headed
uv run pytest tests/test_import.py                                 # one file
uv run pytest tests/test_import.py::TestDatafeeder::test_import_url  # one method (all its cases)
uv run pytest -k parquet                                           # one case by id
uv run pytest --headed=false                                       # headless
```

Tests only depend on the local stack. `tests/test_import.py` imports the files in `files/` by
URL from a server the tests start on port `8765` (`E2E_FILES_PORT`), and WFS / OGC API Features
from the stack's GeoServer (`geor:public_layer`). The ingestion must reach both under `localhost`,
which holds with the local executor (`make up-no-airflow`); with Airflow, set `E2E_HOST` (e.g.
`host.docker.internal`).

`tests/test_import_local_file.py` uploads the files in `files/`. The CSV lat/lon case is skipped
unless `EPSG:2154` is in the backend `PROJECTIONS` setting.

## Generate with playwright

```bash
uv run playwright codegen http://localhost:8080
```

## Worker memory

Watch the airflow-worker container's memory usage while a test run triggers an import:

```bash
./watch-worker-mem.sh [container] [interval_seconds]  # defaults: datafeeder-airflow-worker-1, 2
```
