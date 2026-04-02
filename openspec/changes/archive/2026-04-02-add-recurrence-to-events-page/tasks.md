## 1. Frontend — Add recurrence display to EventsComponent

- [x] 1.1 Update `apps/frontend/src/app/features/events/events.component.ts` — add `recurrence` signal (`RecurrenceResponse | null`), `presets` signal (`RecurrencePresetItem[]`), and fetch both from `getIntegrityLinkRecurrenceIngestionIntegrityLinkIntegrityLinkIdRecurrenceGet` and `listRecurrencePresetsIngestionRecurrencePresetsGet` in `ngOnInit` (parallel calls)
- [x] 1.2 Update `apps/frontend/src/app/features/events/events.component.html` — add `<app-recurrence-selector [recurrence]="recurrence()" [presets]="presets()" [disabled]="true" />` below the page title, before the events list
- [x] 1.3 Import `RecurrenceSelectorComponent` in the component's `imports` array

> **Checkpoint:** Recurrence combobox is visible on the events page in read-only mode.

## 2. Frontend — Tests

- [x] 2.1 Update `apps/frontend/src/app/features/events/events.component.spec.ts` — add tests for recurrence display: preset label shown, cronstrue description for custom cron, placeholder when no recurrence

## 3. Final verification

- [x] 3.1 [P] Run `npm run format` in `apps/frontend`
- [x] 3.2 [P] Run frontend test suite and confirm no regressions
