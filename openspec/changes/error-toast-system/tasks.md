## 1. ErrorToastStore (core/stores)

- [x] 1.1 Create `apps/frontend/src/app/core/stores/error-toast.store.ts` with `toasts = signal<ErrorToast[]>([])`, `add(operationKey: string, error?: unknown): void` and `remove(id: string): void` methods; `add()` computes `translationKey` as `error.error.detail` (when `error` is an `HttpErrorResponse` with a string `detail`) or `errors.operation.${operationKey}` otherwise
- [x] 1.2 Define `ErrorToast` interface `{ id: string; translationKey: string }` in `apps/frontend/src/app/core/models/error-toast.model.ts`
- [x] 1.3 Register `ErrorToastStore` as `providedIn: 'root'`
- [x] 1.4 Write vitest unit tests for `ErrorToastStore`: add, remove, stacking order, error detail override, fallback when no detail

## 2. ErrorToastComponent (shared)

- [x] 2.1 Use the Figma MCP to retrieve the exact design spec for nodes `1119:21582` and `1119:22005` in file `IwMxmE9G9D9StF2QLlR1uE` before implementing the component
- [x] 2.2 Create `apps/frontend/src/app/shared/components/error-toast/error-toast.component.ts` as a standalone OnPush presentational component
- [x] 2.3 Inject `ErrorToastStore` and expose `toasts` signal; emit dismiss to call `remove(id)`
- [x] 2.4 Implement template matching Figma design: orange/peach background (`#ffe5c8`), red border, warning-triangle icon, `toast.translationKey | translate` message, close (×) button; stack toasts vertically with most recent at bottom
- [x] 2.5 Style with Tailwind classes; fixed overlay positioning (floats above all content)
- [x] 2.6 Write vitest unit tests: renders toasts, dismiss button calls store, stacking order

## 3. Mount in root layout

- [x] 3.1 Identify the root layout component (AppComponent or datafeeder shell) that is alive across all datafeeder routes
- [x] 3.2 Add `<app-error-toast />` to the root layout template

## 4. i18n keys

- [x] 4.1 Add `i18n` marker attributes in the template for all operation name strings:
  - `errors.operation.metadataSave`
  - `errors.operation.gnPublish`
  - `errors.operation.gnUnpublish`
  - `errors.operation.gnRightsEdit`
  - `errors.operation.gsRightsEdit`
  - `errors.operation.deletion`
- [x] 4.2 Run `npm run i18n:extract` to register keys in all translation files in alphabetical order
- [x] 4.3 Fill in French and English translations for the extracted keys

## 5. Wire metadata save

- [x] 5.1 Locate the metadata save NgRx effect or service call in the metadata feature
- [x] 5.2 In the error handler, call `errorToastStore.add('metadataSave')`
- [x] 5.3 Ensure the save button's `loading` signal is set back to `false` on error

## 6. Wire GeoNetwork publish / unpublish

- [x] 6.1 Locate the publish/unpublish call in `authorizations.component.ts` (`onTogglePublishGn`)
- [x] 6.2 Wire GN publish error → `errorToastStore.add('gnPublish', error)` (passes error so backend `detail` is used as translation key when present)
- [x] 6.3 Wire GN unpublish error → `errorToastStore.add('gnUnpublish', error)`
- [x] 6.4 Re-enable the publish/unpublish toggle on error

## 7. Wire rights editing (GN + GS)

- [x] 7.1 Locate rights editing NgRx effects or service calls
- [x] 7.2 Wire GN rights error → `errorToastStore.add('gnRightsEdit')`
- [x] 7.3 Wire GS rights error → `errorToastStore.add('gsRightsEdit')`
- [x] 7.4 Re-enable rights editing buttons on error

## 8. Wire dataset deletion

- [x] 8.1 Locate the delete NgRx effect or service call
- [x] 8.2 Wire deletion error → `errorToastStore.add('deletion')`
- [x] 8.3 Ensure the dataset row remains in the list on error
- [x] 8.4 Re-enable the delete icon / confirm button on error

## 9. Wire GeoServer publish / unpublish

- [x] 9.1 Locate `onTogglePublishGs` in `authorizations.component.ts`
- [x] 9.2 Wire GS publish error → `errorToastStore.add('gsPublish', error)`
- [x] 9.3 Wire GS unpublish error → `errorToastStore.add('gsUnpublish', error)`
- [x] 9.4 Re-enable the GS publish/unpublish toggle on error
- [x] 9.5 Add `errors.operation.gsPublish` and `errors.operation.gsUnpublish` i18n keys and run `npm run i18n:extract`

## 10. Fix toast positioning relative to app container

- [ ] 10.0.1 Add `relative` to the outer div in `main-layout.component.html` (the `div.bg-beige.h-full` wrapper)
- [ ] 10.0.2 Move `<app-error-toast />` inside that outer div (currently a sibling after it)
- [ ] 10.0.3 In `error-toast.component.html`, change `fixed` → `absolute` and replace `top-36` with `top-4` (no longer needed to dodge an external header)

## 11. End-to-end verification

- [ ] 11.1 Manually trigger each operation failure (mock or dev environment) and verify the correct toast appears
- [ ] 11.2 Verify toast persists across navigation (go to another route while toast is visible)
- [ ] 11.3 Verify multiple simultaneous toasts stack correctly with most recent at bottom
- [ ] 11.4 Verify each toast dismisses independently
- [ ] 11.5 Verify toast position is not affected by the geOrchestra header (visible within app bounds, not overlapping header)
- [x] 11.6 Run `npm run lint` and `npm run test` — no regressions

## Future (when recurrence editing is implemented)

- [ ] F.1 Wire recurrence edit error → `errorToastStore.add('recurrenceEdit')` in the recurrence feature
- [ ] F.2 Add `errors.operation.recurrenceEdit` i18n key and run `npm run i18n:extract`
- [ ] F.3 Re-enable recurrence edit button on error
