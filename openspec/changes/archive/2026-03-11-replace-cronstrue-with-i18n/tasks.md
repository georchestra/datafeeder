## 1. Translations

- [x] 1.1 [P] Add singular/plural `import.recurrence.freq.*` i18n keys to `apps/frontend/translations/en.json` for all 6 units (m, h, d, w, M, y): `.one` = "Every minute/hour/…", `.other` = "Every {{count}} minutes/hours/…"
- [x] 1.2 [P] Add singular/plural `import.recurrence.freq.*` i18n keys to `apps/frontend/translations/fr.json` for all 6 units with correct French phrasing
- [x] 1.3 [P] Add stub English-style `import.recurrence.freq.*` keys to `de.json`, `es.json`, `it.json`, `nl.json`, `pt.json`, `sk.json`

## 2. Component refactor

- [x] 2.1 Remove `import cronstrue from 'cronstrue/i18n'` from `apps/frontend/src/app/shared/components/recurrence-selector/recurrence-selector.component.ts`
- [x] 2.2 Delete the `frequencyToDisplayCron` export function and its JSDoc comment
- [x] 2.3 Replace the label generation in `options = computed(...)` with direct `TranslateService.instant()` calls using `import.recurrence.freq.<unit>.one` / `.other` key selection based on `n === 1`
- [x] 2.4 Keep fallback: if freq code does not match pattern, use raw code as label

## 3. Tests

- [x] 3.1 Remove the `describe('frequencyToDisplayCron', ...)` block and `frequencyToDisplayCron` import from `recurrence-selector.component.spec.ts`
- [x] 3.2 Update the `'should produce a non-empty cronstrue label for each option'` test to assert `import.recurrence.freq.*` key format (or provide translations in the test and assert the rendered string)

## 4. Dependency cleanup

- [x] 4.1 Remove `cronstrue` from `dependencies` in `apps/frontend/package.json` and run `npm install` in `apps/frontend/`

## 5. Quality

- [x] 5.1 Run `npm run format` in `apps/frontend/` and fix any issues
- [x] 5.2 Run full frontend test suite (`npm test` in `apps/frontend/`) and verify all tests pass
