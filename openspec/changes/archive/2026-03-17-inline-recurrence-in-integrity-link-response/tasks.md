## 1. Backend — Model

- [x] 1.1 Add `preset_id: str | None = None` field to `IntegrityLinkResponse` in `apps/backend/src/models/data_import.py`

## 2. Backend — Route

- [x] 2.1 In `get_integrity_link` (`apps/backend/src/api/routes/ingestion/integrity_link.py`), import `RecurrencePreset` from `src.models.recurrence` and set `response.preset_id` from `RecurrencePreset.from_cron(integrity_link.schedule)` after `model_validate`
- [x] 2.2 Remove the `get_integrity_link_recurrence` endpoint function from `apps/backend/src/api/routes/ingestion/recurrence.py`
- [x] 2.3 Remove unused imports (`RecurrenceResponse`) from `apps/backend/src/api/routes/ingestion/recurrence.py` if no longer referenced

## 3. Backend — Tests

- [x] 3.1 Add/update test in `apps/backend/tests/` for `GET /ingestion/integrity-link/{id}` asserting `preset_id` is returned correctly for a known preset, null schedule, and unknown cron
- [x] 3.2 Add/update test asserting `GET /ingestion/integrity-link/{id}/recurrence` returns 404 (endpoint removed)

## 4. Frontend — Generated API client

- [x] 4.1 Delete `apps/frontend/src/app/core/api/fn/ingestion/get-integrity-link-recurrence-ingestion-integrity-link-integrity-link-id-recurrence-get.ts`
- [x] 4.2 Remove the two lines re-exporting `GetIntegrityLinkRecurrenceIngestionIntegrityLinkIntegrityLinkIdRecurrenceGet$Params` and `getIntegrityLinkRecurrenceIngestionIntegrityLinkIntegrityLinkIdRecurrenceGet` from `apps/frontend/src/app/core/api/functions.ts`

## 5. Frontend — EventsComponent

- [x] 5.1 In `apps/frontend/src/app/features/events/events.component.ts`, remove the import of `getIntegrityLinkRecurrenceIngestionIntegrityLinkIntegrityLinkIdRecurrenceGet` and the `this.api.invoke(...)` call that fetches recurrence
- [x] 5.2 Derive recurrence display from `this.integrityLinkStore.integrityLink()` — construct a `RecurrenceResponse`-shaped object using `{ cron: link.schedule, preset_id: link.preset_id }` and pass it to the `RecurrenceSelectorComponent` input
- [x] 5.3 Remove the `RecurrenceResponse` import if it is no longer used elsewhere in the component

## 6. Frontend — Tests

- [x] 6.1 Update `apps/frontend/src/app/features/events/events.component.spec.ts`: remove all mock branches and assertions referencing `getIntegrityLinkRecurrenceIngestionIntegrityLinkIntegrityLinkIdRecurrenceGet`
- [x] 6.2 Update the mock `integrityLink` signal values in the spec to include `preset_id` and verify the recurrence display is driven from the store
