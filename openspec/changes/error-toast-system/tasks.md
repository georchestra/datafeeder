## 1. ErrorToastStore (core/stores)

- [x] 1.1 Create `apps/frontend/src/app/core/stores/error-toast.store.ts` with `toasts = signal<ErrorToast[]>([])`, `add(operationKey: string, error?: unknown): void` and `remove(id: string): void` methods; `add()` computes `translationKey` as `error.error.detail` (when `error` is an `HttpErrorResponse` with a string `detail`) or `errors.operation.${operationKey}` otherwise
- [x] 1.2 Define `ErrorToast` interface `{ id: string; translationKey: string }` in `apps/frontend/src/app/core/models/error-toast.model.ts`
- [x] 1.3 Register `ErrorToastStore` as `providedIn: 'root'`
- [ ] 1.4 Write vitest unit tests for `ErrorToastStore`: add, remove, stacking order, error detail override, fallback when no detail

## 2. ErrorToastComponent (shared)

- [ ] 2.1 Use the Figma MCP to retrieve the exact design spec for nodes `1119:21582` and `1119:22005` in file `IwMxmE9G9D9StF2QLlR1uE` before implementing the component
- [ ] 2.2 Create `apps/frontend/src/app/shared/components/error-toast/error-toast.component.ts` as a standalone OnPush presentational component
- [ ] 2.3 Inject `ErrorToastStore` and expose `toasts` signal; emit dismiss to call `remove(id)`
- [ ] 2.4 Implement template matching Figma design: orange/peach background (`#ffe5c8`), red border, warning-triangle icon, `toast.translationKey | translate` message, close (×) button; stack toasts vertically with most recent at bottom
- [ ] 2.5 Style with Tailwind classes; fixed overlay positioning (floats above all content)
- [ ] 2.6 Write vitest unit tests: renders toasts, dismiss button calls store, stacking order

## 3. Mount in root layout

- [ ] 3.1 Identify the root layout component (AppComponent or datafeeder shell) that is alive across all datafeeder routes
- [ ] 3.2 Add `<app-error-toast />` to the root layout template

## 4. i18n keys

- [ ] 4.1 Add `i18n` marker attributes in the template for all operation name strings:
  - `errors.operation.metadataSave`
  - `errors.operation.gnPublish`
  - `errors.operation.gnUnpublish`
  - `errors.operation.gnRightsEdit`
  - `errors.operation.gsRightsEdit`
  - `errors.operation.deletion`
- [ ] 4.2 Run `npm run i18n:extract` to register keys in all translation files in alphabetical order
- [ ] 4.3 Fill in French and English translations for the extracted keys

## 5. Wire metadata save

- [ ] 5.1 Locate the metadata save NgRx effect or service call in the metadata feature
- [ ] 5.2 In the error handler, call `errorToastStore.add('metadataSave')`
- [ ] 5.3 Ensure the save button's `loading` signal is set back to `false` on error

## 6. Wire GeoNetwork publish / unpublish

- [ ] 6.1 Locate the publish/unpublish call in `authorizations.component.ts` (`onTogglePublishGn`)
- [ ] 6.2 Wire GN publish error → `errorToastStore.add('gnPublish', error)` (passes error so backend `detail` is used as translation key when present)
- [ ] 6.3 Wire GN unpublish error → `errorToastStore.add('gnUnpublish', error)`
- [ ] 6.4 Re-enable the publish/unpublish toggle on error

## 7. Wire rights editing (GN + GS)

- [ ] 7.1 Locate rights editing NgRx effects or service calls
- [ ] 7.2 Wire GN rights error → `errorToastStore.add('gnRightsEdit')`
- [ ] 7.3 Wire GS rights error → `errorToastStore.add('gsRightsEdit')`
- [ ] 7.4 Re-enable rights editing buttons on error

## 8. Wire dataset deletion

- [ ] 8.1 Locate the delete NgRx effect or service call
- [ ] 8.2 Wire deletion error → `errorToastStore.add('deletion')`
- [ ] 8.3 Ensure the dataset row remains in the list on error
- [ ] 8.4 Re-enable the delete icon / confirm button on error

## 9. Wire GeoServer publish / unpublish

- [ ] 9.1 Locate `onTogglePublishGs` in `authorizations.component.ts`
- [ ] 9.2 Wire GS publish error → `errorToastStore.add('gsPublish', error)`
- [ ] 9.3 Wire GS unpublish error → `errorToastStore.add('gsUnpublish', error)`
- [ ] 9.4 Re-enable the GS publish/unpublish toggle on error
- [ ] 9.5 Add `errors.operation.gsPublish` and `errors.operation.gsUnpublish` i18n keys and run `npm run i18n:extract`

## 10. End-to-end verification

- [ ] 10.1 Manually trigger each operation failure (mock or dev environment) and verify the correct toast appears
- [ ] 10.2 Verify toast persists across navigation (go to another route while toast is visible)
- [ ] 10.3 Verify multiple simultaneous toasts stack correctly with most recent at bottom
- [ ] 10.4 Verify each toast dismisses independently
- [ ] 10.5 Run `npm run lint` and `npm run test` — no regressions

## Future (when recurrence editing is implemented)

- [ ] F.1 Wire recurrence edit error → `errorToastStore.add('recurrenceEdit')` in the recurrence feature
- [ ] F.2 Add `errors.operation.recurrenceEdit` i18n key and run `npm run i18n:extract`
- [ ] F.3 Re-enable recurrence edit button on error
