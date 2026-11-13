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
uv run pytest                                                      # all tests, headless
uv run pytest --headed                                             # watch the browser
uv run pytest tests/test_import.py                                 # one file
uv run pytest tests/test_import.py::TestDatafeeder::test_import_url  # one method (all its cases)
uv run pytest -k parquet                                           # one case by id
```

Tests only depend on the local stack. `tests/test_import.py` imports the files in `files/` by
URL from a server the tests start on port `8765` (`E2E_FILES_PORT`), and WFS / OGC API Features
from the stack's GeoServer (`geor:public_layer`). The ingestion must reach both under `localhost`,
which holds with the local executor (`make up-no-airflow`); with Airflow, set `E2E_HOST` (e.g.
`host.docker.internal`).

`tests/test_import_local_file.py` uploads the files in `files/`. The CSV lat/lon case is skipped
unless `EPSG:2154` is in the backend `PROJECTIONS` setting (the CI sets it).

The FTP and Basic Auth tests skip themselves when their credentials are missing from `.env`.
They are not covered in CI: the secrets are not set, and are never available to fork PRs.

## Test data

The files in `files/` are open data, under the [Licence Ouverte 2.0 (Etalab)](https://www.etalab.gouv.fr/licence-ouverte-open-licence/).
They are extracts or format conversions of the original datasets.

| File | Source |
| --- | --- |
| `mel_mairie.*`, `mel_mairie_export_qgis.csv`, `mel_mairie_latin9_qgis.zip` | Métropole Européenne de Lille, [Mairies de la Métropole Européenne de Lille](https://www.data.gouv.fr/datasets/mairies-de-la-metropole-europeenne-de-lille-1) |
| `subventions_aux_associations.csv` | Métropole Européenne de Lille, [Subventions attribuées par la MEL à destination des associations](https://www.data.gouv.fr/datasets/subventions-attribuees-par-la-mel-a-destination-des-associations) |
| `bruit_zones_calmes.json` | Métropole Européenne de Lille, [Zones Calmes - Diagnostic PPBE](https://www.data.gouv.fr/datasets/zones-calmes-diagnostic-ppbe-plan-de-prevention-du-bruit-dans-lenvironnement) |
| `travaux_7j_30k_troncon.json` | Métropole Européenne de Lille, [Tronçons de voirie impactés par des travaux](https://www.data.gouv.fr/datasets/troncons-de-voirie-impactes-par-des-travaux) |
| `bruit_travaux.gpkg` | The two datasets above, as two layers of one GeoPackage |
| `a-epci2025.parquet` | IGN Admin Express COG, published by icem7 on data.gouv.fr: [Communes, cantons et Epci 2025](https://www.data.gouv.fr/datasets/communes-cantons-et-epci-2025-admin-express-cog-plus-ign) |

## Generate with playwright

```bash
uv run playwright codegen http://localhost:8080
```

## Worker memory

Watch the airflow-worker container's memory usage while a test run triggers an import:

```bash
./watch-worker-mem.sh [container] [interval_seconds]  # defaults: datafeeder-airflow-worker-1, 2
```
