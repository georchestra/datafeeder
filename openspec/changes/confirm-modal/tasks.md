## 1. Feature Integration — integrity-link-list

- [ ] 1.1 Update `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.ts`: inject `MatDialog` from `@angular/material/dialog`; import `ConfirmationDialogComponent` and `ConfirmationDialogData` from `geonetwork-ui`; replace `window.confirm()` in `deleteIntegrityLink()` with `matDialog.open(ConfirmationDialogComponent, { data: { title, message, confirmText, cancelText, focusCancel: 'cancel' } })`; convert `dialogRef.afterClosed()` to a Promise and proceed only when result is `true`
- [ ] 1.2 Remove the `TranslateService` injection if it is no longer used after the migration (was used only for `translate.instant()` in the confirm call); keep it if still needed elsewhere in the component
- [ ] 1.3 Run `npm run format` in `apps/frontend/` and verify no ESLint/TypeScript errors

## 2. Tests

- [ ] 2.1 Update `apps/frontend/src/app/features/integrity-link-list/integrity-link-list.component.spec.ts`: replace `vi.spyOn(window, 'confirm')` mock with a mock for `MatDialog.open()` returning an object with `afterClosed()` emitting `true` or `undefined`; update scenarios — "calls delete API when modal confirmed", "does not call delete API when modal cancelled"

## 3. Validation

- [ ] 3.1 Manual smoke test: delete a dataset — verify the in-app modal appears (not the browser native dialog), confirm deletes and removes the row, cancel leaves the row intact
- [ ] 3.2 Manual test: press Escape while modal is open — verify modal closes without deleting
- [ ] 3.3 Manual test: click the backdrop — verify modal closes without deleting
