## 1. ErrorToastService (core)

- [ ] 1.1 Create `apps/frontend/src/app/core/services/error-toast.service.ts` with `toasts = signal<ErrorToast[]>([])`, `add(operationKey: string): void` and `remove(id: string): void` methods
- [ ] 1.2 Define `ErrorToast` interface `{ id: string; operationKey: string }` in `apps/frontend/src/app/core/models/error-toast.model.ts`
- [ ] 1.3 Register `ErrorToastService` as `providedIn: 'root'`
- [ ] 1.4 Write vitest unit tests for `ErrorToastService`: add, remove, stacking order

## 2. ErrorToastComponent (shared)

- [ ] 2.1 Create `apps/frontend/src/app/shared/components/error-toast/error-toast.component.ts` as a standalone OnPush presentational component
- [ ] 2.2 Inject `ErrorToastService` and expose `toasts` signal as computed input; emit `dismiss` to call `remove(id)`
- [ ] 2.3 Implement template matching Figma design: orange/peach background (`#ffe5c8`), red border, warning-triangle icon, operation message via `translate` pipe, close (×) button; stack toasts vertically with most recent at bottom
- [ ] 2.4 Style with Tailwind classes; fixed overlay positioning (floats above all content)
- [ ] 2.5 Write vitest unit tests: renders toasts, dismiss button calls service, stacking order

## 3. Mount in root layout

- [ ] 3.1 Identify the root layout component (AppComponent or data-publisher shell) that is alive across all data-publisher routes
- [ ] 3.2 Add `<app-error-toast />` to the root layout template

## 4. i18n keys

- [ ] 4.1 Add ngx-translate keys for all operation names in all translation files (`fr.json`, `en.json` etc.):
  - `errors.operation.metadataSave`
  - `errors.operation.gnPublish`
  - `errors.operation.gsPublish`
  - `errors.operation.gngsUnpublish`
  - `errors.operation.gnRightsEdit`
  - `errors.operation.gsRightsEdit`
  - `errors.operation.recurrenceEdit`
  - `errors.operation.deletion`
- [ ] 4.2 Add the toast wrapper message key `errors.toast.message` → `"{{ operation }} a rencontré une erreur"` (or equivalent per translation)

## 5. Wire metadata save

- [ ] 5.1 Locate the metadata save NgRx effect or service call in the metadata feature
- [ ] 5.2 In the error handler, call `errorToastService.add('metadataSave')`
- [ ] 5.3 Ensure the save button's `loading` signal is set back to `false` on error

## 6. Wire publish / unpublish (GN + GS)

- [ ] 6.1 Locate publish/unpublish NgRx effects or service calls
- [ ] 6.2 Wire GN publish error → `errorToastService.add('gnPublish')`
- [ ] 6.3 Wire GS publish error → `errorToastService.add('gsPublish')`
- [ ] 6.4 Wire unpublish error → `errorToastService.add('gngsUnpublish')`
- [ ] 6.5 Re-enable publish/unpublish buttons on error

## 7. Wire rights editing (GN + GS)

- [ ] 7.1 Locate rights editing NgRx effects or service calls
- [ ] 7.2 Wire GN rights error → `errorToastService.add('gnRightsEdit')`
- [ ] 7.3 Wire GS rights error → `errorToastService.add('gsRightsEdit')`
- [ ] 7.4 Re-enable rights editing buttons on error

## 8. Wire recurrence editing

- [ ] 8.1 Locate recurrence editing NgRx effect or service call
- [ ] 8.2 Wire recurrence error → `errorToastService.add('recurrenceEdit')`
- [ ] 8.3 Re-enable recurrence edit button on error

## 9. Wire dataset deletion

- [ ] 9.1 Locate the delete NgRx effect or service call
- [ ] 9.2 Wire deletion error → `errorToastService.add('deletion')`
- [ ] 9.3 Ensure the dataset row remains in the list on error
- [ ] 9.4 Re-enable the delete icon / confirm button on error

## 10. End-to-end verification

- [ ] 10.1 Manually trigger each operation failure (mock or dev environment) and verify the correct toast appears
- [ ] 10.2 Verify toast persists across navigation (go to another route while toast is visible)
- [ ] 10.3 Verify multiple simultaneous toasts stack correctly with most recent at bottom
- [ ] 10.4 Verify each toast dismisses independently
- [ ] 10.5 Run `npm run lint` and `npm run test` — no regressions
