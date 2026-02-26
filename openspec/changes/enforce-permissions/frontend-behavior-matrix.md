# Frontend Page Behavior Matrix

> Frontend page behavior depending on the backend endpoint response.

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Works correctly, user sees expected content |
| ⚠️ | Partial — error logged to console but no user feedback |
| ❌ | Broken — unhandled error, blank page, no feedback |
| 🟢 | Error properly displayed to user (inline alert) |

## Page: `/` — Dataset List

| Backend Response | `access_level` per row | Frontend Behavior | Error Visible? |
|------------------|----------------------|-------------------|----------------|
| 200 + items (ADMIN) | All rows `"ADMIN"` | All rows clickable, full opacity, no badge | N/A |
| 200 + items (OWNER) | Own `"OWNER"`, shared `"WRITE"`/`"READ"` | OWNER/WRITE rows clickable; READ rows `opacity-60`, `cursor-default`, "readOnly" badge | N/A |
| 200 + items (WRITE) | Matching rows `"WRITE"`/`"OWNER"` | Same per-row logic as above | N/A |
| 200 + items (READ only) | Matching rows `"READ"` | Rows visible but greyed out, not clickable | N/A |
| 200 + empty (NO_PERM) | No items returned | "No items" message displayed | N/A |
| Network error / 500 | — | `console.error` only, `loading=false`, empty list shown | ⚠️ **No** |

## Page: `/:id` — Layout Shell (parent of edit/events/authorizations)

Calls `GET /ingestion/integrity-link/{id}` on init. This is the **critical gate** for all child pages.

| Backend Response | Frontend Behavior | Error Visible? | Sidebar State |
|------------------|-------------------|----------------|---------------|
| 200 + `access_level: "ADMIN"` | Store populated, child route renders | N/A | All links enabled, Reconfigure button shown |
| 200 + `access_level: "OWNER"` | Store populated, child route renders | N/A | All links enabled, Reconfigure button shown |
| 200 + `access_level: "WRITE"` | Store populated, child route renders | N/A | Authorizations/Events → disabled `<span>`, Reconfigure → hidden |
| **403** (READ user) | **Unhandled promise rejection** — store stays `null` | ❌ **No** | Sidebar renders with defaults (`isOwnerOrAdmin=false`), content area blank |
| **403** (NO_PERM user) | Same as READ: unhandled rejection | ❌ **No** | Same broken state |
| **404** (invalid ID) | Unhandled promise rejection | ❌ **No** | Same broken state |
| Network error / 500 | Unhandled promise rejection | ❌ **No** | Same broken state |

```
What happens on 403 at /:id:

  IntlinkLayoutComponent.ngOnInit()
          │
          ▼
  api.invoke(GET /integrity-link/{id})
          │
          ▼ 403
  Promise rejects (no try/catch)
          │
          ▼
  Angular default ErrorHandler → console.error (dev mode)
          │
          ▼
  store.integrityLink = null (never set)
  store.isOwnerOrAdmin() = false
          │
          ▼
  Sidebar renders (authorizations/events disabled)
  <router-outlet> renders child component
  Child component sees store.integrityLink() = null
          │
          ▼
  ┌─────────────────────────────────────────┐
  │ User sees: sidebar + blank content area │
  │ No error message, no redirect           │
  └─────────────────────────────────────────┘
```

## Page: `/:id/edit` — Metadata Editor

Assumes layout shell (`/:id`) loaded successfully.

| Backend Response (GeoNetwork proxy) | Frontend Behavior | Error Visible? |
|-------------------------------------|-------------------|----------------|
| 200 (record loads) | geonetwork-ui metadata editor renders | ✅ N/A |
| `metadata_id` is `null` | Shows "not available yet" + link to import page | ✅ Informational |
| 403 from GeoNetwork proxy | Observable subscription error (no error callback) | ⚠️ **No** — `console.error` only |
| 404 / 500 from GeoNetwork | Same — silent Observable error | ⚠️ **No** |

## Page: `/:id/events` — Events List

Assumes layout shell loaded successfully.

| Backend Response | Frontend Behavior | Error Visible? |
|------------------|-------------------|----------------|
| 200 + dag runs | Events list renders with statuses | ✅ N/A |
| 200 + empty list | "No events" message | ✅ Informational |
| **403** (WRITE/READ navigates via URL) | `console.error` only, empty events shown | ⚠️ **No** |
| 404 / 500 | `console.error` only | ⚠️ **No** |
| Log download 200 | Text file download triggered | ✅ N/A |
| Log download error | `console.error` only | ⚠️ **No** |

## Page: `/:id/authorizations` — Access Rights

Assumes layout shell loaded successfully.

| Backend Response | Frontend Behavior | Error Visible? |
|------------------|-------------------|----------------|
| 200 + rules list | Rules table renders with add/edit/delete | ✅ N/A |
| **403** (WRITE user navigates via URL) | **Unhandled promise rejection** — no try/catch | ❌ **No** — blank/broken page |
| Rule PUT 200 | Rule saved, list refreshes | ✅ N/A |
| Rule DELETE 200 | Rule deleted, list refreshes | ✅ N/A |
| Rule PUT/DELETE 403 | **Unhandled promise rejection** | ❌ **No** |
| Groups 200 | Dropdowns populated | ✅ N/A |
| Network error / 500 | **Unhandled promise rejection** | ❌ **No** |

## Page: `/import` — Import Wizard

| Backend Response | Frontend Behavior | Error Visible? |
|------------------|-------------------|----------------|
| POST staging 200 | Moves to configuration step, starts DAG polling | ✅ N/A |
| POST staging 4xx/5xx | `importError` signal → red `UiAlertBox` | 🟢 **Yes** |
| DAG poll timeout | `timeoutError` translation displayed | 🟢 **Yes** |
| GET metadata 200 | Column config editor renders | ✅ N/A |
| GET metadata 403 | Error displayed in preview area | 🟢 **Yes** |
| GET preview 200 | Data table renders | ✅ N/A |
| GET preview error | Falls back to raw preview, then displays error | 🟢 **Yes** |
| PUT metadata 200 | Config saved, preview refreshes | ✅ N/A |
| PUT metadata error | `previewError` signal displayed | 🟢 **Yes** |
| POST process 200 | Navigates to `/:id/events` | ✅ N/A |
| POST process 403 | `validationError` signal displayed | 🟢 **Yes** |

## Error Handling Summary

| Page | 403 Handling | User Feedback | Has try/catch? | Has error UI? |
|------|-------------|---------------|----------------|---------------|
| `/` (list) | N/A (filtered) | N/A | ✅ Yes | No (not needed) |
| `/:id` (layout shell) | ❌ None | ❌ Blank page | No | No |
| `/:id/edit` | ⚠️ Silent | ❌ Blank content | Sync only | No |
| `/:id/events` | ⚠️ console.error | ❌ Empty events | ✅ Yes | No |
| `/:id/authorizations` | ❌ None | ❌ Blank/broken | No | No |
| `/import` | ✅ Full | 🟢 Inline alerts | ✅ Yes | ✅ Yes |

## Critical Playwright Test Scenarios

These are real-user paths that lead to a broken UX:

| # | Scenario | How User Gets There | What Happens |
|---|----------|---------------------|--------------|
| 1 | READ user types `/:id/edit` in URL bar | Saw dataset id in list (greyed out), copies URL | Layout 403 → blank page, no error message |
| 2 | WRITE user navigates to `/:id/authorizations` via URL | Normal navigation + URL edit | Layout loads OK, but `GET /rules` → 403 → unhandled |
| 3 | WRITE user types `/:id/events` in URL bar | Same pattern | Layout loads OK, but `GET /runs/{intlink_id}` → 403 → console error only |
| 4 | Stale tab: user had WRITE, admin revokes, user clicks row | Clicked a cached "clickable" row | Layout detail 403 → blank page |
