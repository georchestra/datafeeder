## 1. Backend — Configuration & Model

- [x] 1.1 [P] Add `RECURRENCE_FREQUENCIES` and `RECURRENCE_EXECUTION_HOUR` settings to `apps/backend/src/core/config.py`
- [x] 1.2 [P] Update `IntegrityLink.schedule` field `max_length` from 10 to 20 in `apps/backend/src/models/integrity_link.py`
- [x] 1.3 Add Alembic migration to alter `datakern.integrity_link.schedule` column to `VARCHAR(20)`
- [x] 1.4 Add optional `recurrence_frequency: str | None = None` field to `ProcessRequest` in `apps/backend/src/models/data_import.py`

> **Checkpoint**: Settings load correctly, model accepts longer schedule values.

## 2. Backend — Recurrence Service

- [x] 2.1 Create `apps/backend/src/services/recurrence_service.py` with `parse_frequency(freq: str) -> tuple[int, str]` function
- [x] 2.2 Implement `frequency_to_cron(freq: str, execution_hour: int, reference_date: date) -> str` with conversion rules for all units (m, h, d, w, M, y)
- [x] 2.3 Handle Feb 29 edge case — cap day-of-month to 28
- [x] 2.4 Implement `validate_frequency(freq: str, allowed: list[str]) -> bool` to check format and membership in allowed list
- [x] 2.5 Write unit tests for recurrence service in `apps/backend/tests/services/test_recurrence_service.py` covering all conversion scenarios and edge cases

> **Checkpoint**: All cron conversion unit tests pass.

## 3. Backend — API Integration

- [x] 3.1 Extend `SettingsService.get_all_settings()` in `apps/backend/src/services/settings_service.py` to include `recurrence_frequencies` and `recurrence_execution_hour`
- [x] 3.2 Update the process endpoint in `apps/backend/src/api/routes/ingestion/process.py` to accept `recurrence_frequency`, validate it, convert to cron, and persist `schedule` + `schedule_enabled` on `IntegrityLink`
- [x] 3.3 Write integration tests for the process endpoint with recurrence in `apps/backend/tests/api/test_process_recurrence.py`
- [x] 3.4 Write test for settings endpoint returning recurrence frequencies in `apps/backend/tests/services/test_settings_service.py`

> **Checkpoint**: Backend API returns frequencies in settings and persists schedule via process endpoint.

## 4. Frontend — API Client Regeneration

- [x] 4.1 Regenerate the frontend API client after backend changes (`make run-sync-script` or follow `frontend-api-sync` skill)
- [x] 4.2 Verify generated types include `recurrence_frequency` on `ProcessRequest` and new settings fields

> **Checkpoint**: Frontend TypeScript types are in sync with backend.

## 5. Frontend — Recurrence Selector Component

- [x] 5.1 Install `cronstrue` npm package in `apps/frontend/`
- [x] 5.2 [P] Add i18n translations for recurrence labels in `apps/frontend/translations/` (fr.json and en.json): frequency labels, tooltip text, selector placeholder
- [x] 5.3 Create presentational `RecurrenceSelectorComponent` at `apps/frontend/src/app/shared/components/recurrence-selector/` — inputs: frequencies list, staging_retrieve_time; output: selected frequency; disabled options with tooltip for frequencies below retrieve time
- [x] 5.4 Write vitest unit tests for `RecurrenceSelectorComponent` covering: display for remote source, hidden for local file, grayed-out frequencies, tooltip, default empty selection

> **Checkpoint**: Recurrence selector component renders correctly in isolation.

## 6. Frontend — Wizard Integration

- [x] 6.1 Fetch recurrence frequencies from settings in the ingestion wizard store/service
- [x] 6.2 Integrate `RecurrenceSelectorComponent` into step 2 of `DataImportWizardComponent` (`apps/frontend/src/app/shared/components/data-import-wizard/`), visible only when source type is not `file`
- [x] 6.3 Pass the selected `recurrence_frequency` to the `processStagingDataIngestionProcessPost` API call
- [x] 6.4 Write vitest integration test for the wizard step 2 with recurrence selector

> **Checkpoint**: End-to-end flow works — user selects recurrence in wizard, backend persists cron schedule.

## 7. Validation & Cleanup

- [x] 7.1 Run `make fix-all-python` and fix any linting issues
- [x] 7.2 Run `npm run format` in `apps/frontend/` and fix any linting issues
- [x] 7.3 Run full backend test suite and verify all tests pass
- [x] 7.4 Run full frontend test suite and verify all tests pass
