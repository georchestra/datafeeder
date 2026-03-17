## Context

The `RecurrenceSelectorComponent` generates human-readable labels for frequency codes (e.g. `"2d"`, `"1h"`) by converting them to cron expressions and passing them to `cronstrue`. This produces verbose labels that expose the internal scheduled time ("At 12:00 AM, every 2 days") rather than the simpler user-facing intent ("Every 2 days").

The project already uses `ngx-translate` for all UI strings. There is no reason to involve cron syntax in label generation — the frequency codes themselves carry all the information needed.

## Goals / Non-Goals

**Goals:**
- Labels read "Every N units" — no time-of-day detail exposed
- Proper singular/plural per locale (e.g. "Every 1 day" vs "Every 2 days")
- Remove the `cronstrue` npm package entirely
- Keep the same fallback behavior for unknown codes (raw code string)

**Non-Goals:**
- Grammatical gender agreement beyond singular/plural (e.g. French "Tous les" vs "Toutes les" — acceptable simplification)
- Dynamic/arbitrary cron expression display (not needed here)

## Decisions

### D1: Translate directly from frequency code, not via cron

**Choice**: Parse `{n, unit}` from the frequency code and look up `import.recurrence.freq.<unit>.one` or `.other` via `TranslateService.instant()`.

**Rationale**: The cron representation is purely an implementation artifact. Translating directly from the source format is simpler, more readable, and removes the dependency on `frequencyToDisplayCron` (which was only needed to feed cronstrue). The `frequencyToDisplayCron` export and its tests can be removed.

### D2: Singular/plural via two i18n key variants per unit

**Choice**: Use two key variants per unit:
- `import.recurrence.freq.<unit>.one` → "Every day" / "Chaque jour"
- `import.recurrence.freq.<unit>.other` → "Every {{count}} days" / "Tous les {{count}} jours"

Key selection: `n === 1 ? '.one' : '.other'`.

**Rationale**: `ngx-translate` does not support ICU plural syntax natively without adding `ngx-translate-messageformat-compiler` (an additional dependency). Two explicit key variants are simpler, already idiomatic in this codebase, and cover all needed cases.

**Alternatives considered**: ICU plural format — rejected (requires extra dep, no existing usage in project).

### D3: Remove `frequencyToDisplayCron` export

**Choice**: Delete `frequencyToDisplayCron` function and its unit tests.

**Rationale**: It was only used to satisfy cronstrue's input format. Once the cron intermediate step is gone, the function has no purpose. Its test coverage is replaced by the new label generation tests.

### D4: Non-FR/EN locales get English-style stubs

**Choice**: Fill `de`, `es`, `it`, `nl`, `pt`, `sk` with English strings as stubs.

**Rationale**: These locales currently have mostly empty translations across the codebase. Matching existing practice avoids inconsistency. Native translations can be added later.

## Risks / Trade-offs

- **[Risk] frequencyToDisplayCron is exported and used in tests** → Mitigation: remove both the export and the `describe('frequencyToDisplayCron')` block in the spec file as part of the same change.
- **[Risk] Unknown/custom frequency codes still fall back to raw code** → Acceptable and unchanged behavior; no mitigation needed.

## Migration Plan

Frontend-only change, no data migration needed:
1. Add i18n keys to all 8 locale files
2. Refactor `RecurrenceSelectorComponent` label logic
3. Update spec file (remove cronstrue assertions, add i18n label assertions)
4. Remove `cronstrue` from `package.json` and run `npm install`
5. Run `npm run format` and `npm test`
