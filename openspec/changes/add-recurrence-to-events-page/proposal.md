## Why

The events page (`/:intlink_id/events`) shows the DAG run history for a dataset but provides no visibility into the active recurrence schedule. Users who land on this page to inspect past events have no context about how the dataset is scheduled to run next. The recurrence combobox (already on the metadata page) should also appear on the events page as a read-only summary.

## What Changes

- Add a read-only recurrence combobox to the events page, displaying the current recurrence schedule for the dataset
- Reuse `RecurrenceSelectorComponent` (already exists) in disabled mode — preset label via i18n, cronstrue description for custom crons, placeholder when no schedule
- Fetch recurrence from the existing `GET /ingestion/integrity-link/{id}/recurrence` endpoint

## Capabilities

### New Capabilities

- None

### Modified Capabilities

- `recurrence-presets`: Add scenario — recurrence is displayed in read-only mode on the events page in addition to the metadata page

## Impact

- Frontend only — no backend changes required
- Affected files: `apps/frontend/src/app/features/events/events.component.ts`, `events.component.html`, `events.component.spec.ts`
- Depends on `RecurrenceSelectorComponent` and `getIntegrityLinkRecurrenceIngestionIntegrityLinkIntegrityLinkIdRecurrenceGet` API function (both already available)
