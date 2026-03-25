## Why

The current scheduling approach relies on a configurable list of frequency codes (`RECURRENCE_FREQUENCIES` env var) that are converted to cron expressions at process time. This design is over-engineered for our actual needs: we only support a small, fixed set of recurrence options (daily, weekly, bi-monthly). It also prevents displaying custom cron expressions that admins may set directly in the database, and the recurrence is only configurable during the initial ingestion wizard—not visible afterward on dataset detail pages.

## What Changes

- **BREAKING**: Remove the `RECURRENCE_FREQUENCIES` setting and `RECURRENCE_EXECUTION_HOUR` from backend config; remove the `recurrence_frequencies` and `recurrence_execution_hour` fields from the `GET /settings` response
- **BREAKING**: Replace the `recurrence_frequency` field in `ProcessRequest` with a `recurrence` enum accepting named presets (`EVERY_DAY`, `EVERY_WEEK`, `EVERY_TWO_MONTHS`) or `null`
- Backend defines hardcoded preset pairs: enum label → cron expression (e.g., `EVERY_DAY` → `0 4 */1 * *`)
- Remove `recurrence_service.py` (frequency parsing, cron conversion); replace with a simple preset-to-cron mapping
- Add a new `GET /ingestion/integrity-link/{id}/recurrence` endpoint returning the current schedule as either a known preset label or the raw cron string (for admin-modified values)
- Frontend replaces the `RecurrenceSelectorComponent` (dynamic frequency list + i18n label generation) with a simpler preset combobox using translated labels for known presets and cronstrue for custom cron display
- Display recurrence as a **read-only combobox** on the dataset detail page (accessible from the Figma design node `1119-21266`)
- Editing recurrence and per-user permissions are deferred to a later change

## Capabilities

### New Capabilities

- `recurrence-presets`: Defines the hardcoded recurrence presets (enum + cron mapping), the new recurrence API endpoint, and the frontend read-only display with cronstrue fallback for custom crons

### Modified Capabilities

- `ingestion-recurrence`: Removes configurable frequency list, replaces frequency-based submission with preset-based submission, updates process endpoint contract
- `recurrence-frequency-labels`: Replaces dynamic label generation from frequency codes with static translated labels per preset + cronstrue fallback

## Impact

- **Backend** (full-stack change):
  - `apps/backend/src/core/config.py` — Remove `RECURRENCE_FREQUENCIES`, `RECURRENCE_EXECUTION_HOUR` settings
  - `apps/backend/src/services/recurrence_service.py` — Delete entirely
  - `apps/backend/src/services/settings_service.py` — Remove recurrence fields
  - `apps/backend/src/api/routes/settings.py` — Update response model
  - `apps/backend/src/api/routes/ingestion/process.py` — Change from frequency to preset enum
  - `apps/backend/src/models/data_import.py` — Update request/response models
  - New: preset enum + mapping module, recurrence endpoint
- **Frontend**:
  - `apps/frontend/src/app/shared/components/recurrence-selector/` — Rewrite to preset-based + cronstrue
  - `apps/frontend/src/app/shared/components/data-import-wizard/` — Update recurrence integration
  - Dataset detail page — Add read-only recurrence display
  - Translation files — Replace dynamic frequency keys with preset label keys
  - New dependency: `cronstrue` for human-readable cron descriptions
- **API contract**: Breaking changes to `POST /ingestion/process` and `GET /settings`; new endpoint `GET /ingestion/integrity-link/{id}/recurrence`
- **Tests**: Backend recurrence service tests rewritten; frontend selector tests updated; new endpoint tests
- **ELT**: No change — DAG generator already reads raw cron from `IntegrityLink.schedule`
