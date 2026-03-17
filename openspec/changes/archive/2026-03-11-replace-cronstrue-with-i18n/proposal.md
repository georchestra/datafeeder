## Why

The `RecurrenceSelectorComponent` uses `cronstrue` to produce human-readable option labels by converting frequency codes to cron expressions and back (e.g. `"2d"` → `"0 0 */2 * *"` → `"At 12:00 AM, every 2 days"`). The result is over-specific — it exposes the internal scheduled time — when users only need to know the period (e.g. "Every 2 days"). The project already uses `ngx-translate` for all UI text; cronstrue is an unneeded dependency.

## What Changes

- Remove the `cronstrue` npm package from `apps/frontend/`
- Remove the `frequencyToDisplayCron` helper function (cron intermediate step no longer needed)
- Replace the cronstrue label generation with direct `ngx-translate` key lookup using singular/plural variants
- Add `import.recurrence.freq.*` i18n keys to all locale files (`en`, `fr`, and stubs for `de`, `es`, `it`, `nl`, `pt`, `sk`)
- Update `RecurrenceSelectorComponent` to derive labels via `TranslateService` directly from frequency codes
- Update unit tests to reflect the new label format

## Capabilities

### New Capabilities
<!-- none — this is a pure implementation refactor -->

### Modified Capabilities
<!-- none — spec-level behavior is unchanged: the component still displays a human-readable label for each frequency option -->

## Impact

- **Frontend only** — no backend or ELT changes
- `apps/frontend/src/app/shared/components/recurrence-selector/recurrence-selector.component.ts` — label generation logic
- `apps/frontend/src/app/shared/components/recurrence-selector/recurrence-selector.component.spec.ts` — test assertions
- `apps/frontend/translations/*.json` — add 12 new keys per locale (6 units × singular/plural)
- `apps/frontend/package.json` — remove `cronstrue` dependency
