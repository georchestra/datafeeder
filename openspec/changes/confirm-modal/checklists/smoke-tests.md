# Smoke Tests — delete-dataset + confirm-modal

**Purpose**: Manual end-to-end validation of the dataset deletion feature and in-app confirmation modal  
**Changes covered**: [`delete-dataset`](../../delete-dataset/tasks.md) · [`confirm-modal`](../tasks.md)  
**Prerequisite**: Application running locally with several datasets visible in the dashboard (ideally: one with a recurrent schedule, one without)

---

## Setup

- [ ] Log in as **User A** (owner of at least two datasets, one with a recurrent schedule)
- [ ] Log in in a second session as **User B** (not owner of User A's datasets)
- [ ] Log in in a third session as an **Admin** user
- [ ] Navigate to the dataset list (integrity-link-list view)

---

## 1. Hover-State Trash Icon

- [ ] Mouse over a dataset row — a trash icon appears on the right of the row
- [ ] Mouse away from the row — the trash icon disappears
- [ ] Other rows are unaffected while hovering a given row

---

## 2. Confirmation Modal — Display

- [ ] Click the trash icon on any row — an **in-app modal** opens (not the browser native dialog)
- [ ] The modal shows a semi-transparent backdrop that blocks interaction with the list behind it
- [ ] The modal displays a title and a confirmation message
- [ ] The modal has two buttons: **"Supprimer"** (confirm) and **"Annuler"** (cancel)
- [ ] The **"Annuler"** button receives initial keyboard focus (safe default for destructive actions)

---

## 3. Cancel — No Delete

- [ ] Click the trash icon to open the modal, then click **"Annuler"**
- [ ] The modal closes; the dataset row **remains** in the list
- [ ] DevTools Network tab: no `DELETE` request was sent

- [ ] Open the modal, then press **Escape**
- [ ] The modal closes; the dataset row **remains** in the list

- [ ] Open the modal, then click the semi-transparent backdrop outside the modal panel
- [ ] The modal closes; the dataset row **remains** in the list

---

## 4. Successful Deletion — Owner, No Schedule

- [ ] As **User A**, click the trash icon on a dataset **without** a recurrent schedule
- [ ] Confirm in the modal
- [ ] The modal closes; the row disappears from the list immediately (no full page reload)
- [ ] DevTools Network tab: `DELETE /api/ingestion/integrity-link/{id}` → **204**
- [ ] Reload the page — the dataset no longer appears in the list
- [ ] In GeoServer: the corresponding layer no longer exists
- [ ] In GeoNetwork: the corresponding metadata record no longer exists
- [ ] In the database: the `integrity_link` row and its `integrity_link_rule` rows are gone (cascade)

---

## 5. Successful Deletion — Owner, With Recurrent Schedule

- [ ] As **User A**, click the trash icon on a dataset **with** a recurrent schedule
- [ ] Confirm in the modal → `DELETE` returns **204**
- [ ] The row disappears from the list
- [ ] In Airflow: the corresponding DAG no longer appears (verify in Airflow UI or via API)
- [ ] GeoServer layer, GeoNetwork record, and DB row are also removed (same checks as §4)

---

## 6. Successful Deletion — Admin Deleting Another User's Dataset

- [ ] As the **Admin**, navigate to the dataset list (or use a direct URL with a known ID owned by User A)
- [ ] Delete the dataset via the trash icon and confirm
- [ ] `DELETE` returns **204**; the row disappears; resources are removed (same checks as §4)

---

## 7. Permission — Non-Owner Blocked

- [ ] As **User B**, navigate to a dataset owned by User A (if visible)
- [ ] Click the trash icon and confirm
- [ ] DevTools Network tab: `DELETE /api/ingestion/integrity-link/{id}` → **403**
- [ ] The dataset row **remains** in the list

---

## 8. DAG Deletion Failure → 500, Dataset Preserved

> Simulate an Airflow failure (e.g. stop the Airflow service or temporarily block its endpoint via a proxy).

- [ ] As **User A**, attempt to delete a dataset **with** a recurrent schedule while Airflow is unavailable
- [ ] Confirm in the modal
- [ ] DevTools Network tab: `DELETE` → **500**
- [ ] The dataset row **remains** in the list (frontend does not remove it on error)
- [ ] GeoServer, GeoNetwork, and database are **unchanged** (no partial cleanup)

---

## 9. Best-Effort Cleanup — GeoServer / GeoNetwork Unavailable

> Simulate GeoServer or GeoNetwork being unavailable (stop the service or block its endpoint).

- [ ] Delete a dataset while GeoServer is unreachable — `DELETE` still returns **204**
- [ ] The row is removed from the list; the DB row is gone
- [ ] Server logs show a warning for the failed GeoServer step but no fatal error

---

## 10. Keyboard Accessibility

- [ ] Click the trash icon to open the modal
- [ ] Press **Tab** repeatedly — focus cycles only between the two modal buttons (focus trap active)
- [ ] Confirm or cancel — focus returns to the element that triggered the modal

---

## 11. Internationalisation

- [ ] With the UI in **French**: modal shows "Supprimer" / "Annuler"
- [ ] With the UI in **English**: modal shows "Delete" / "Cancel"

---

## Notes

_Record any unexpected behaviour here before marking tasks 8.1–8.4 in [delete-dataset/tasks.md](../../delete-dataset/tasks.md) and tasks 3.1–3.3 in [confirm-modal/tasks.md](../tasks.md) as complete._
