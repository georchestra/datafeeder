## Context

The datafeeder module lets users manage existing datasets: save metadata, publish/unpublish via GeoNetwork/GeoServer, edit access rights, configure recurrence, and delete datasets. These operations can fail (network errors, backend validation, external service unavailability), but today the frontend provides no feedback on failure — buttons may return to their idle state silently, leaving the user unaware the operation had no effect.

Note: recurrence editing is not yet implemented in the frontend. Toast wiring for that operation will be added when the recurrence feature is built.

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
The store holds `toasts = signal<ErrorToast[]>([])` where each `ErrorToast` has `{ id: string; operationKey: string }`. Components call `errorToastStore.add(operationKey)` and `errorToastStore.remove(id)`.

`operationKey` maps to an ngx-translate key pattern: `errors.operation.<key>` (e.g. `errors.operation.metadataSave`).

**Alternatives considered:**
- NgRx action/reducer: overkill for ephemeral UI state with no persistence requirement.
- BehaviorSubject: signals are the Angular 20 idiomatic pattern and integrate better with zoneless OnPush.

### 3. Component location: `shared/components/error-toast/`
The `ErrorToastComponent` is purely presentational (receives `toasts` via input signal, emits `dismiss` events). It is mounted once in `AppComponent` (or the main layout component) so it stays alive across routes.

**Layout**: absolutely positioned overlay (fixed, bottom-right or centered per Figma), using `z-index` to float above all content. No CDK Overlay dependency — the component is simply rendered in the root layout template.

### 4. Button re-enable pattern
Feature components that trigger operations use a `loading = signal(false)` pattern. On error, the signal is set back to `false`. No new abstraction needed — this is already the expected pattern in the codebase.

### 5. Operation coverage
The following feature services/effects will catch errors and call `errorToastStore.add(operationKey)`:

| Operation | Operation key | Location |
|---|---|---|
| Metadata save | `metadataSave` | metadata feature service / NgRx effect |
| GN publish | `gnPublish` | authorizations component |
| GN unpublish | `gnUnpublish` | authorizations component |
| GN rights edit | `gnRightsEdit` | authorizations component |
| GS rights edit | `gsRightsEdit` | authorizations component |
| Deletion | `deletion` | integrity-link-list component |
| GS publish/unpublish | `gsPublish` / `gsUnpublish` | *(not yet implemented)* |
| Recurrence edit | `recurrenceEdit` | *(not yet implemented)* |

## Risks / Trade-offs

- **Multiple simultaneous errors** → Toasts stack (most recent at bottom). No limit enforced; edge case where many errors fire at once may produce a long list. Mitigation: acceptable per spec; user can dismiss each one.
- **Operation key typos** → A missing translation key shows the key itself in production. Mitigation: add the translation keys in the same PR as the service; lint/test will catch missing keys if a translation guard is added.
- **Root layout assumption** → Mounting `ErrorToastComponent` in `AppComponent` works only if all datafeeder views share that root. If modal/dialog routes use a different outlet, the component may not render. Mitigation: verify layout structure during implementation; if needed, mount in the datafeeder shell component instead.

## Migration Plan

No data migration required. This is a pure frontend addition:
1. Add `ErrorToastStore` to `core/stores/`.
2. Add `ErrorToastComponent` to `shared/components/`.
3. Mount `<app-error-toast>` in the root layout template.
4. Add source i18n keys and run `npm run i18n:extract` to register them in all translation files.
5. Wire each implemented feature's error handler to call `errorToastStore.add(key)`.
6. Re-enable buttons on error in each feature component.
7. Wire GeoServer publish/unpublish and recurrence editing when those features are implemented.

Rollback: revert the PR. No state is persisted outside the browser session.

## Open Questions

- Which component is the "root layout" for the datafeeder module? (`AppComponent`, a shell component, or a named router outlet host?) → Clarify during implementation to pick the right mount point.
- Should deletion error use a specific message that includes the dataset title, or is the generic operation-name message sufficient? → Default to generic (consistent with spec); can be enhanced later.
