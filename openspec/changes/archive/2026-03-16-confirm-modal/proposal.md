## Why

The dataset delete action uses `window.confirm()` for user confirmation — a native browser dialog that doesn't match the application design system, cannot be styled or translated consistently, and blocks the main thread. A reusable, in-app modal confirmation component is needed to complete the delete-dataset feature with proper UX.

## What Changes

- **Reuse `ConfirmationDialogComponent`** from `geonetwork-ui` — the library already used for `ButtonComponent`; no new component to build or maintain
- **Replace `window.confirm()`** in `integrity-link-list` — the delete flow opens `ConfirmationDialogComponent` via `MatDialog` (already a direct dependency)
- **i18n integration** — title, message, and button labels are resolved by the caller via `TranslateService`; no hardcoded text
- **Accessible by default** — focus trap, keyboard (Escape to cancel), focus starts on Cancel button for destructive actions

## Capabilities

### New Capabilities

- `confirm-modal`: In-app confirmation modal for destructive actions — uses `ConfirmationDialogComponent` from `geonetwork-ui` opened via `MatDialog`. No new component built; caller provides translated title, message, and button labels.

### Modified Capabilities

<!-- No existing spec-level behavior changes required -->

## Impact

- **Frontend only** — no backend, ELT, or database changes
- `apps/frontend/src/app/features/integrity-link-list/` — updated to use `MatDialog.open(ConfirmationDialogComponent)` instead of `window.confirm()`
- `apps/frontend/translations/` — new i18n keys added (`common.cancel`, `common.delete`, `dashboard.deleteDataset`, `dashboard.deleteDatasetConfirm`)
- `geonetwork-ui: 2.9.0-dev.60c0e5e0d` and `@angular/material: 20.2.14` are both direct dependencies — no new packages needed
