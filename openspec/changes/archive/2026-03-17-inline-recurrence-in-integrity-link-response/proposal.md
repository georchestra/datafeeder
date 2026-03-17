## Why

`GET /ingestion/integrity-link/{id}/recurrence` duplicates data already stored on `IntegrityLink.schedule`, requiring a second round-trip to fetch information that could be included directly in the existing `GET /ingestion/integrity-link/{id}` response.

## What Changes

- Add `preset_id: str | None` to `IntegrityLinkResponse` (derived from `schedule` via `RecurrencePreset.from_cron()`).
- **BREAKING** Remove `GET /ingestion/integrity-link/{integrity_link_id}/recurrence` endpoint.
- Frontend `EventsComponent` reads `cron`/`preset_id` from the already-loaded `IntegrityLinkStore` instead of invoking the dedicated recurrence endpoint.
- Delete the generated frontend API client file for the removed endpoint and its export from `functions.ts`.

## Capabilities

### New Capabilities

_(none)_

### Modified Capabilities

- `ingestion-recurrence`: The recurrence state (cron + preset_id) for a given IntegrityLink is now read from `IntegrityLinkResponse` instead of a dedicated `/recurrence` endpoint. The requirement for reading recurrence via a separate GET is replaced by a requirement to expose those fields on the integrity-link response.

## Impact

- `apps/backend/src/models/data_import.py` — add `preset_id: str | None` field to `IntegrityLinkResponse`
- `apps/backend/src/api/routes/ingestion/integrity_link.py` — populate `preset_id` in `get_integrity_link`
- `apps/backend/src/api/routes/ingestion/recurrence.py` — remove `get_integrity_link_recurrence` endpoint
- `apps/frontend/src/app/features/events/events.component.ts` — remove call to deleted endpoint; derive recurrence from `IntegrityLinkStore`
- `apps/frontend/src/app/features/events/events.component.spec.ts` — update mocks
- `apps/frontend/src/app/core/api/fn/ingestion/get-integrity-link-recurrence-*.ts` — delete generated file
- `apps/frontend/src/app/core/api/functions.ts` — remove re-export of deleted function
