## Why

The ingestion tunnel allows users to configure remote data sources (URL, FTP) whose access credentials are retained, but there is currently no way to set up a recurring ingestion schedule through the UI. The database model already has `schedule` and `schedule_enabled` fields on `IntegrityLink`, and the Airflow DAG generator already supports dynamic scheduled re-ingestion — but the backend exposes no API to write these fields, and the frontend has only a disabled placeholder in the sidebar. Users need a way to choose a recurrence frequency during ingestion configuration so that data is automatically re-ingested at regular intervals.

## What Changes

- **Backend settings**: Add a configurable list of allowed recurrence frequencies (e.g. `1m`, `1h`, `1d`, `1w`, `1M`, `1y`) and a configurable nocturnal execution hour for cron generation.
- **Backend recurrence service**: New service that validates a frequency value, converts it to a cron expression (respecting nocturnal hour for daily+ frequencies, anchoring to current day-of-month for monthly+ frequencies, handling Feb 29→28 edge case).
- **Backend API**: New endpoint to retrieve the list of allowed recurrence frequencies. Extend the process endpoint (or add a dedicated endpoint) to accept and persist the `schedule` field on `IntegrityLink`.
- **Backend settings endpoint**: Expose the recurrence frequency list via the existing settings service so the frontend can fetch it dynamically.
- **Frontend ingestion wizard (step 2)**: Add a recurrence selector component on the configuration step, visible only for remote sources. Frequencies shorter than the dataset's retrieval time are grayed out with a tooltip.
- **Frontend i18n**: Add translations for recurrence labels; consider using `cronstrue` for human-readable cron descriptions.

## Capabilities

### New Capabilities

- `ingestion-recurrence`: Configurable recurrence frequency selection during ingestion, with backend cron conversion and frontend UI integration in the ingestion wizard step 2.

### Modified Capabilities

_(none — no existing spec-level requirements are changing)_

## Impact

- **Backend** (`apps/backend/`):
  - `core/config.py` — new settings: `RECURRENCE_FREQUENCIES`, `RECURRENCE_EXECUTION_HOUR`
  - `services/` — new recurrence service for cron conversion logic
  - `services/settings_service.py` — expose recurrence frequencies
  - `api/routes/ingestion/process.py` — accept schedule in process request
  - `models/data_import.py` — uncomment/add `cron_schedule` on `ProcessRequest`
- **Frontend** (`apps/frontend/`):
  - New recurrence selector component (shared or feature-level)
  - `data-import-wizard` step 2 template and component updated
  - New translations in `translations/` for recurrence labels
  - Possible new dependency: `cronstrue` npm package
- **ELT** (`apps/elt/`): No changes needed — Airflow DAG generator already reads `schedule` from `IntegrityLink`.
- **API contract**: New query on settings, extended process request body — non-breaking (additive).
- **Architecture principles**: API-First (§1) — backend endpoint before UI; Component Modularity (§2) — backend, frontend loosely coupled via REST; Angular Architecture (§6) — presentational recurrence selector component.
