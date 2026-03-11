## Context

The delete-dataset feature uses `window.confirm()` for the destructive action confirmation step. This native dialog is unstyled, untestable, blocks the main thread, bypasses `ngx-translate`, and cannot be dismissed with application-level logic. Angular CDK `@angular/cdk/dialog` (`@angular/cdk: 20.2.14`) is already a project dependency and provides a lightweight, accessible foundation for building in-app modals without pulling in Angular Material.

## Goals / Non-Goals

**Goals:**

- Replace `window.confirm()` in `integrity-link-list` with a styled, accessible in-app modal
- Create a reusable `ConfirmModalComponent` in `shared/components/` usable by future features
- Leverage `@angular/cdk/dialog` (already available) — no new package installs
- Keep the component presentational and data-driven (title, message, labels passed as config)
- Maintain full testability with vitest

**Non-Goals:**

- A general-purpose modal/dialog system (forms, wizards, side panels)
- Replacing all existing alerts or notification patterns
- Backend or ELT changes

## Decisions

### 1. Angular CDK Dialog over custom overlay

**Decision**: Use `@angular/cdk/dialog` (`Dialog.open()` + `DIALOG_DATA`) as the host mechanism.

**Rationale**: CDK Dialog already ships with the project, provides focus trap, keyboard dismissal (Escape), ARIA `role="dialog"` / `aria-modal`, and backdrop click-to-close. Building a custom overlay with `@angular/cdk/overlay` would duplicate all of this.

**Alternative**: Custom `<dialog>` element (native HTML). Rejected — no focus trap polyfill, less Angular-idiomatic, harder to control programmatically in a zoneless app.

**Alternative**: Angular Material `MatDialog`. Rejected — would add Material as a dependency; CDK alone is sufficient and already present.

---

### 2. Component data contract via `DIALOG_DATA` injection token

**Decision**: Pass config to the component via Angular CDK's `DIALOG_DATA` injection token. The component is opened imperatively from the caller.

```
ConfirmModalData {
  title: string           // already-translated string
  message: string         // already-translated string
  confirmLabel?: string   // default "Confirm"
  cancelLabel?: string    // default "Cancel"
  variant?: 'danger' | 'warning'  // default 'danger'
}
```

The caller is responsible for resolving translations before opening (via `TranslateService.instant()`). The modal component itself is purely presentational — no i18n dependency inside.

**Rationale**: Keeps the component simple and maximally reusable. The caller knows the translation context; the modal does not need to.

**Alternative**: Pass translation keys and let the modal resolve them internally. Rejected — adds an `ngx-translate` dependency inside a generic shared component and couples it to the translation namespace.

---

### 3. Result via `DialogRef.closed` observable (Promise-wrapped by caller)

**Decision**: The caller converts `dialogRef.closed` to a Promise and awaits the boolean result (`true` = confirmed, `undefined`/`false` = cancelled). This fits the existing `async/await` style of `deleteIntegrityLink()`.

```
                 ┌─────────────────────────┐
Caller           │  dialog.open(           │
(integrity-link) │    ConfirmModalComponent│
                 │    { data: config }     │
                 │  )                      │
                 └────────────┬────────────┘
                              │ DialogRef
                              ▼
                 ┌─────────────────────────┐
                 │  ConfirmModalComponent  │
                 │  ┌────────────────────┐ │
                 │  │  Title             │ │
                 │  │  Message           │ │
                 │  │  [Cancel] [Delete] │ │
                 │  └────────────────────┘ │
                 └────────────┬────────────┘
                              │ dialogRef.close(true|undefined)
                              ▼
                 Caller receives boolean,
                 proceeds or aborts delete
```

---

### 4. Placement: `shared/components/confirm-modal/`

**Decision**: Lives in `shared/components/` — it is a presentational, reusable organism.

**Rationale**: Matches the `shared/` layering rule: reusable presentational components go in `shared/`, features go in `features/`. The modal has no feature-specific logic.

---

### 5. Styling: Tailwind CSS, no custom SCSS

**Decision**: Style entirely with Tailwind utility classes. Danger variant uses `red-600` destructive button. No separate `.scss` file.

**Rationale**: Consistent with the project's Tailwind-first approach. The `ui-alert-box` component is a reference for color/variant conventions.

## Risks / Trade-offs

- **CDK Dialog z-index / backdrop** — CDK sets its overlay container at a high z-index, which should work with the current layout. If the app later adds a sticky toolbar or side nav with very high z-index, stacking context may need adjustment → low risk for now.
- **Zoneless compatibility** — CDK Dialog 20.x is fully signal/zoneless compatible. No `ChangeDetectorRef` hacks needed.
- **`DIALOG_DATA` in tests** — vitest tests must provide `DIALOG_DATA` via `TestBed` providers. This is straightforward but slightly more setup than a plain `@Input()` component. Documented in tasks.

## Migration Plan

1. Create `ConfirmModalComponent` in `shared/components/confirm-modal/`
2. Update `integrity-link-list` to inject `Dialog` and call `dialog.open()` in place of `window.confirm()`
3. Update vitest tests for `IntegrityLinkListComponent` (mock `Dialog.open()`)
4. Update translations (no key renames — existing keys are reused)

No rollback complexity — `window.confirm()` can be restored by reverting two lines in the feature component if needed.

## Open Questions

~~None — CDK Dialog approach is well-established, no unknowns.~~
