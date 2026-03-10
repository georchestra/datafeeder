## Why

DataFeeder currently allows editing and saving permission rules on datasets (IntegrityLinkRule), but these rules are not enforced. Any authenticated user can access any dataset's endpoints, view any dataset in the list, and navigate to any detail page regardless of permissions. This is a security gap: authorization is purely cosmetic. Backend enforcement (HTTP 403) and frontend conditional navigation must be implemented to make the permission system functional.

This is a full-stack change touching backend (API authorization) and frontend (conditional navigation/UI).

## What Changes

- **Backend**: Add authorization checks to all protected dataset endpoints. Unauthorized requests return HTTP 403 Forbidden. The dataset list endpoint filters results based on user permissions.
- **Frontend**: Conditionally show/hide navigation links and action buttons based on the user's effective permissions on each dataset. Display backend 403 errors when users manually navigate to unauthorized URLs.
- **Permission model enforcement**:
  - Dataset list visibility requires at least METADATA READ (or ownership/admin).
  - Dataset detail access and metadata proxy require METADATA WRITE (or ownership/admin).
  - Rights editing, events, recurrence, reconfigure, delete require ownership or admin.
  - WRITE implicitly includes READ.
  - Owner always has full access without explicit rules.
  - Administrators bypass all checks.

## Capabilities

### New Capabilities

- `enforce-permissions`: Backend authorization enforcement (HTTP 403) on all protected dataset endpoints, dataset list visibility filtering, and frontend conditional navigation based on effective permissions.

### Modified Capabilities

(none)

## Impact

- **Backend API** (`apps/backend/src/api/routes/`): All dataset-related endpoints gain authorization checks. The dataset list endpoint query changes to filter by user permissions.
- **Backend services** (`apps/backend/src/services/`): New permission-checking service or utility.
- **Backend core** (`apps/backend/src/core/security.py`): Authorization logic integrated with existing auth context.
- **Frontend features** (`apps/frontend/src/app/features/`): Dataset list and detail views gain permission-aware rendering. Navigation links conditionally enabled/disabled.
- **Frontend API client**: Permission data included in API responses for frontend decision-making.
- **No database schema changes**: IntegrityLinkRule model already exists.
- **No breaking API changes**: Endpoints remain the same; unauthorized calls now return 403 instead of succeeding.
