## Context

The datafeeder module lets users manage existing datasets: save metadata, publish/unpublish via GeoNetwork/GeoServer, edit access rights, configure recurrence, and delete datasets. These operations can fail (network errors, backend validation, external service unavailability), but today the frontend provides no feedback on failure — buttons may return to their idle state silently, leaving the user unaware the operation had no effect.

Note: recurrence editing exists in the ingestion tunnel and reconfiguration flow, but those views already surface errors to the user — no toast wiring needed there. Recurrence editing in the events page (`events.component`) is not yet implemented; toast wiring will be added there when it is built.

The Figma design (node 1119:21582 / 1119:22005) shows a persistent, dismissable toast component with:

- Orange/peach background (`#ffe5c8`), red border, warning-triangle icon, close (×) button.
- The failed operation name embedded in the message (e.g. "La sauvegarde des métadonnées a rencontré une erreur").
- Multiple toasts stacked, most recent at the bottom.
- Toasts survive page navigation.

## Goals / Non-Goals

**Goals:**

- A single, reusable toast store and component covering all currently-implemented operation types (metadata save, GeoNetwork publish/unpublish, GeoNetwork/GeoServer rights editing, deletion).
- Toasts are persistent (stay until dismissed) and survive Angular router navigation.
- When an error is triggered by a button, that button becomes interactive again immediately.
- Messages include the operation name using i18n keys via ngx-translate.
- Component follows Angular architecture: presentational component + smart store.

**Non-Goals:**

- Success toasts / info notifications (out of scope for this ticket).
- Backend changes — all errors are surfaced from existing HTTP error responses.
- Auto-dismiss / timeout behavior.
- Mobile-specific layout (this is a desktop-only module per Figma).

## Decisions

### 1. Store location: `core/stores/`

The toast store is a singleton managing global UI state across navigation. It belongs in `apps/frontend/src/app/core/stores/error-toast.store.ts`, alongside existing stores like `IntegrityLinkStore`.

**Alternatives considered:**

- Shared feature service: would not survive navigation and could not be referenced by multiple feature modules without creating a circular dependency.
- NgRx store slice: heavier machinery for a simple UI-only list; a signal-based store in `core/stores/` is idiomatic and consistent with the existing architecture.

### 2. State model: Angular signals

The store holds `toasts = signal<ErrorToast[]>([])` where each `ErrorToast` has `{ id: string; translationKey: string }`. Components call `errorToastStore.add(translationKey)` and `errorToastStore.remove(id)`.

`translationKey` is the full ngx-translate key used for the message (e.g. `errors.operation.metadataSave`). In some cases this may be derived from backend error details (such as an `error.detail` field) as long as it resolves to a valid translation key.

**Alternatives considered:**

- NgRx action/reducer: overkill for ephemeral UI state with no persistence requirement.
- BehaviorSubject: signals are the Angular 20 idiomatic pattern and integrate better with zoneless OnPush.

### 3. Component location: `shared/components/error-toast/`

The `ErrorToastComponent` is purely presentational (receives `toasts` via input signal, emits `dismiss` events). It is mounted inside the outer div of `MainLayoutComponent` so it stays alive across routes.

**Layout**: `position: absolute` overlay within a `position: relative` container (the outer `div.h-full` of `main-layout.component.html`). `<app-error-toast />` is placed inside that div. Using `z-index` to float above all content. No CDK Overlay dependency.

**Why not `position: fixed`**: the datafeeder app is deployed inside geOrchestra, which injects a page-level header above `<app-root>`. A `fixed` overlay is positioned relative to the viewport, so its `top` offset would need to hard-code the header height — fragile and environment-dependent. An `absolute` overlay inside a `relative` container that begins below the geOrchestra header is naturally independent of any header injected above the app root.

### 4. Button re-enable pattern

Feature components that trigger operations use a `loading = signal(false)` pattern. On error, the signal is set back to `false`. No new abstraction needed — this is already the expected pattern in the codebase.

### 5. Operation coverage

The following feature services/effects will catch errors and call `errorToastStore.add(operationKey)`:

| Operation       | Operation key    | Location                                       |
| --------------- | ---------------- | ---------------------------------------------- |
| Metadata save   | `metadataSave`   | metadata feature service / NgRx effect         |
| GN publish      | `gnPublish`      | authorizations component                       |
| GN unpublish    | `gnUnpublish`    | authorizations component                       |
| GN rights edit  | `gnRightsEdit`   | authorizations component                       |
| GS rights edit  | `gsRightsEdit`   | authorizations component                       |
| Deletion        | `deletion`       | integrity-link-list component                  |
| GS publish      | `gsPublish`      | authorizations component (`onTogglePublishGs`) |
| GS unpublish    | `gsUnpublish`    | authorizations component (`onTogglePublishGs`) |
| Recurrence edit | `recurrenceEdit` | _(not yet implemented in events page — see note above)_ |

## Risks / Trade-offs

- **Multiple simultaneous errors** → Toasts stack (most recent at bottom). No limit enforced; edge case where many errors fire at once may produce a long list. Mitigation: acceptable per spec; user can dismiss each one.
- **Operation key typos** → A missing translation key shows the key itself in production. Mitigation: add the translation keys in the same PR as the service; lint/test will catch missing keys if a translation guard is added.
- **Root layout assumption** → `ErrorToastComponent` is mounted inside `MainLayoutComponent`'s outer div. All datafeeder views are rendered through the router outlet in that same div, so the component is present for every route. If modal/dialog routes use a different outlet, the component may not render — verify during implementation.

## Migration Plan

No data migration required. This is a pure frontend addition:

1. Add `ErrorToastStore` to `core/stores/`.
2. Add `ErrorToastComponent` to `shared/components/`.
3. Mount `<app-error-toast>` in the root layout template.
4. Add source i18n keys and run `npm run i18n:extract` to register them in all translation files.
5. Wire each implemented feature's error handler to call `errorToastStore.add(key)`.
6. Re-enable buttons on error in each feature component.
7. Wire recurrence editing in `events.component` when that feature is implemented there.

Rollback: revert the PR. No state is persisted outside the browser session.

## Open Questions

- Should deletion error use a specific message that includes the dataset title, or is the generic operation-name message sufficient? → Default to generic (consistent with spec); can be enhanced later.
