## Context

The delete-dataset feature uses `window.confirm()` for the destructive action confirmation step. This native dialog is unstyled, untestable, blocks the main thread, bypasses `ngx-translate`, and cannot be dismissed with application-level logic.

`geonetwork-ui` (already a direct dependency at `2.9.0-dev.60c0e5e0d`) exports a `ConfirmationDialogComponent` specifically designed for destructive-action confirmation. `@angular/material/dialog` (`MatDialog`) is also a direct project dependency (`@angular/material: 20.2.14`) — the underlying host mechanism `ConfirmationDialogComponent` uses. No new packages are needed.

## Goals / Non-Goals

**Goals:**

- Replace `window.confirm()` in `integrity-link-list` with a styled, accessible in-app modal
- Reuse `ConfirmationDialogComponent` from `geonetwork-ui` — consistent with the library already used for `ButtonComponent`
- No new shared component to build or maintain
- Maintain full testability with vitest

**Non-Goals:**

- Building a custom modal/dialog component
- A general-purpose modal/dialog system (forms, wizards, side panels)
- Replacing all existing alerts or notification patterns
- Backend or ELT changes

## Decisions

### 1. Reuse `ConfirmationDialogComponent` from geonetwork-ui

**Decision**: Open `ConfirmationDialogComponent` via `MatDialog.open()` using `ConfirmationDialogData`.

```
ConfirmationDialogData {
  title: string        // already-translated string
  message: string      // already-translated string
  confirmText: string  // already-translated string
  cancelText: string   // already-translated string
  focusCancel: string  // focus target — set to cancel button for destructive actions
}
```

The caller resolves translations via `TranslateService.instant()` before opening. The component itself has no i18n dependency.

**Rationale**: `ConfirmationDialogComponent` exactly matches the use case (title, message, confirm/cancel, focus-on-cancel for destructive actions). Already used in the geonetwork-ui ecosystem alongside `ButtonComponent`. No new components to own, test, or maintain.

**Alternative**: Custom `ConfirmModalComponent` built on Angular CDK Dialog. Rejected — adds a component to own and maintain when an equivalent already exists in the library. CDK Dialog is lower-level and would require building/styling everything from scratch.

**Alternative**: `ModalDialogComponent` from geonetwork-ui. Rejected — its `body` field takes a `TemplateRef<unknown>`, adding unnecessary complexity for a simple text confirmation.

---

### 2. Result via `MatDialogRef.afterClosed()` (Promise-wrapped by caller)

**Decision**: The caller wraps `dialogRef.afterClosed()` as a Promise and awaits the boolean result (`true` = confirmed, `undefined`/`false` = cancelled). This fits the existing `async/await` style of `deleteIntegrityLink()`.

```
                 ┌──────────────────────────────────┐
Caller           │  matDialog.open(                 │
(integrity-link) │    ConfirmationDialogComponent,  │
                 │    { data: confirmationData }    │
                 │  )                               │
                 └──────────────┬───────────────────┘
                                │ MatDialogRef
                                ▼
                 ┌──────────────────────────────────┐
                 │  ConfirmationDialogComponent     │
                 │  (geonetwork-ui)                 │
                 │  ┌──────────────────────────┐   │
                 │  │  Title                   │   │
                 │  │  Message                 │   │
                 │  │  [Cancel*] [Confirm]     │   │
                 │  └──────────────────────────┘   │
                 │  * focus starts on Cancel        │
                 └──────────────┬───────────────────┘
                                │ dialogRef.afterClosed() → true | undefined
                                ▼
                 Caller receives boolean,
                 proceeds or aborts delete
```

## Risks / Trade-offs

- **geonetwork-ui styling** — The component's visual design is owned by geonetwork-ui, not Tailwind/Datafeeder. If the library's dialog style diverges from the app DS in future releases, it will require a library upgrade or override. Low risk given `ButtonComponent` is already used with no visual friction.
- **`focusCancel` field is required** — The interface requires a `focusCancel` string. The component handles this internally; callers pass an identifier string. Verify exact usage from geonetwork-ui source if needed.
- **MatDialog in tests** — vitest tests must mock `MatDialog.open()`, identical effort to the CDK approach.
- **Library version lock** — `2.9.0-dev.60c0e5e0d` is a dev prerelease. If `ConfirmationDialogComponent`'s interface changes in a future version, the integration site is a single call in `integrity-link-list`. Easy to update.

## Migration Plan

1. Update `integrity-link-list` to inject `MatDialog` and call `matDialog.open(ConfirmationDialogComponent, { data })` in place of `window.confirm()`
2. Update vitest tests for `IntegrityLinkListComponent` (mock `MatDialog.open()`)
3. Update translations (no key renames — existing keys are reused)

No rollback complexity — `window.confirm()` can be restored by reverting a few lines in the feature component.

## Open Questions

~~None.~~
