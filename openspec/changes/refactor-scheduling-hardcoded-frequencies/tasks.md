## 1. Backend — Recurrence preset model & mapping

- [x] 1.1 [P] Create `apps/backend/src/models/recurrence.py` with `RecurrencePreset` StrEnum, `PRESET_CRON_MAP`, and `CRON_PRESET_MAP` (inverse dict)
- [x] 1.2 [P] Create `apps/backend/tests/models/test_recurrence.py` — unit tests for preset enum values, cron mappings, and reverse mapping

> **Checkpoint:** Preset model is available for use by routes and services.

## 2. Backend — Update process endpoint

- [x] 2.1 Update `ProcessRequest` in `apps/backend/src/models/data_import.py` — rename `recurrence_frequency` to `recurrence`, type as `RecurrencePreset | None`
- [x] 2.2 Update `apps/backend/src/api/routes/ingestion/process.py` — replace frequency validation + `recurrence_service` calls with direct `PRESET_CRON_MAP` lookup
- [x] 2.3 Update `apps/backend/tests/api/routes/test_process_recurrence.py` — rewrite tests for preset-based submission (valid preset, null, invalid value → 422)

> **Checkpoint:** Process endpoint accepts preset enum, stores correct cron.

## 3. Backend — New recurrence endpoints

- [x] 3.1 Add `RecurrenceResponse` model to `apps/backend/src/models/recurrence.py` with fields `cron: str | None` and `preset_id: str | None`
- [x] 3.2 Add `GET /ingestion/recurrence-presets` route — returns list of `{ "id": "<PRESET_ID>", "cron": "<expression>" }` from `PRESET_CRON_MAP`
- [x] 3.3 Add `GET /ingestion/integrity-link/{id}/recurrence` route — reads `IntegrityLink.schedule`, performs reverse-lookup in `CRON_PRESET_MAP` to resolve `preset_id`
- [x] 3.4 Create `apps/backend/tests/api/routes/test_recurrence_endpoints.py` — tests for both endpoints (preset list, known cron → preset_id, custom cron → preset_id null, null schedule, 404)

> **Checkpoint:** New recurrence API is available. Frontend can be built against it.

## 4. Backend — Clean up old recurrence system

- [x] 4.1 [P] Remove `RECURRENCE_FREQUENCIES` from `apps/backend/src/core/config.py`. Keep `RECURRENCE_EXECUTION_HOUR` as configurable execution hour for daily+ presets
- [x] 4.2 [P] Delete `apps/backend/src/services/recurrence_service.py`
- [x] 4.3 [P] Delete `apps/backend/tests/services/test_recurrence_service.py`
- [x] 4.4 Update `apps/backend/src/services/settings_service.py` — remove recurrence fields from settings dict
- [x] 4.5 Update `apps/backend/src/api/routes/settings.py` — remove `recurrence_frequencies` and `recurrence_execution_hour` from `SettingsResponse`
- [x] 4.6 Remove recurrence-related env vars from `apps/backend/datafeeder.env` if present
- [x] 4.7 Run `make fix-all-python` and verify no import errors or lint issues

> **Checkpoint:** Backend is fully migrated. Old frequency system is gone. Run backend tests.

## 5. Frontend — Install cronstrue & regenerate API client

- [x] 5.1 Install `cronstrue` package: `cd apps/frontend && npm install cronstrue`
- [x] 5.2 Regenerate the frontend API client after backend OpenAPI changes

> **Checkpoint:** Frontend has cronstrue and fresh API types matching new backend.

## 6. Frontend — Rewrite recurrence selector component

- [x] 6.1 Rewrite `apps/frontend/src/app/shared/components/recurrence-selector/recurrence-selector.component.ts` — inputs: preset list + `RecurrenceResponse`; display logic: if `preset_id` → i18n label, else if `cron` → cronstrue with locale, else → placeholder; supports disabled (read-only) mode
- [x] 6.2 Update template in `recurrence-selector.component.html` — Material select with preset options + cronstrue custom display
- [x] 6.3 Remove `FREQUENCY_MIN_SECONDS` constant and staging-retrieve-time filtering logic
- [x] 6.4 Update `recurrence-selector.component.spec.ts` — tests for preset display, cronstrue fallback, disabled state

> **Checkpoint:** Recurrence selector works with presets and cronstrue.

## 7. Frontend — Update import wizard integration

- [x] 7.1 Update `apps/frontend/src/app/shared/components/data-import-wizard/data-import-wizard.component.ts` — fetch preset list from `GET /ingestion/recurrence-presets`, submit preset id in `recurrence` field instead of frequency code
- [x] 7.2 Remove `recurrenceFrequencies` signal dependency on `SettingsService`
- [x] 7.3 Update `data-import-wizard.recurrence.spec.ts` tests

> **Checkpoint:** Import wizard uses preset-based recurrence.

## 8. Frontend — Settings cleanup

- [x] 8.1 Remove `recurrence_frequencies` and `recurrence_execution_hour` from `AppSettings` interface in `apps/frontend/src/app/core/settings/settings.service.ts`

## 9. Frontend — Read-only recurrence on dataset detail page

- [x] 9.1 Fetch recurrence via `GET /ingestion/integrity-link/{id}/recurrence` in the integrity-link store or a dedicated service
- [x] 9.2 Add read-only recurrence combobox to `apps/frontend/src/app/features/metadata/metadata.component.ts` using `RecurrenceSelectorComponent` in disabled mode
- [x] 9.3 Add tests for recurrence display on the metadata page

> **Checkpoint:** Recurrence is visible on dataset detail, matching Figma design.

## 10. Frontend — i18n

- [x] 10.1 Add preset label keys (`recurrence.preset.EVERY_MINUTE`, `recurrence.preset.EVERY_HOUR`, `recurrence.preset.EVERY_DAY`, `recurrence.preset.EVERY_WEEK`, `recurrence.preset.EVERY_MONTH`, `recurrence.preset.EVERY_YEAR`, `recurrence.none`) in all translation files (en, fr, de, es, it, nl, pt, sk)
- [x] 10.2 Remove old `import.recurrence.freq.*` keys and `import.recurrence.tooltip.disabled`

## 11. Final verification

- [x] 11.1 Run full backend test suite
- [x] 11.2 Run full frontend test suite
- [x] 11.3 Run linters: `make fix-all-python` + `npm run format`
