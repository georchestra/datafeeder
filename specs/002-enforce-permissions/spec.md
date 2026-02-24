# Feature Specification: Enforce Permissions on Dataset Actions

**Feature Branch**: `002-enforce-permissions`  
**Created**: 2025-02-24  
**Status**: Draft  
**Input**: User description: "Un utilisateur appartient à un groupe. Un jeu de données est constitué d'une métadonnée et d'une donnée. La gestion des droits se fait séparément pour la métadonnée et la donnée. Les actions internes soumises à autorisation incluent : visualisation de la liste, édition des métadonnées, édition des droits, visualisation des événements, planification de la récurrence d'ingestion, reconfiguration et suppression d'un jeu de données. L'édition et la sauvegarde des droits ont déjà été implémentées. Il s'agit d'appliquer les règles d'autorisation côté backend (403) et côté frontend (navigation conditionnelle)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dataset List Visibility Based on Group Permissions (Priority: P1)

A user who is not the owner of a dataset can see it in the dataset list only if a permission rule (READ or WRITE on METADATA) exists for their group on that dataset. A user belongs to exactly one group. When no such rule exists, the dataset does not appear in the list. The owner of a dataset always sees it in the list. Administrators see all datasets.

**Why this priority**: The dataset list is the main entry point into the application. Without proper visibility filtering, users see datasets they have no access to, or cannot see datasets they should have access to.

**Independent Test**: A user whose group has been granted READ on METADATA for a given dataset logs in and sees that dataset in the list. A user whose group has no permission on the dataset does not see it.

**Acceptance Scenarios**:

1. **Given** a dataset owned by User A and a METADATA READ rule for Group X, **When** User B (member of Group X) views the dataset list, **Then** the dataset appears in the list.
2. **Given** a dataset owned by User A and a METADATA WRITE rule for Group X, **When** User B (member of Group X) views the dataset list, **Then** the dataset appears in the list.
3. **Given** a dataset owned by User A with no rules for Group Y, **When** User C (member of Group Y) views the dataset list, **Then** the dataset does not appear in the list.
4. **Given** a dataset owned by User A, **When** User A views the dataset list, **Then** the dataset always appears.
5. **Given** any dataset, **When** an administrator views the dataset list, **Then** all datasets appear.

---

### User Story 2 - Backend Rejects Unauthorized Actions with 403 (Priority: P1)

When an authenticated user attempts an action on a dataset they are not authorized for, the backend responds with HTTP 403 Forbidden. This applies to: viewing dataset details, accessing the metadata proxy (which handles both reading and writing metadata via GeoNetwork), viewing and editing rights, viewing events and downloading logs, scheduling ingestion recurrence, reconfiguring a dataset (via the ingestion tunnel endpoints called with an existing dataset identifier), and deleting a dataset.

**Why this priority**: Without backend enforcement, authorization is purely cosmetic. Any user who knows a dataset identifier could bypass the frontend and directly call the API. Backend enforcement is the security foundation.

**Independent Test**: A user with no permissions on a dataset calls any protected endpoint and receives a 403 response.

**Acceptance Scenarios**:

1. **Given** a dataset owned by User A and User B with no permission rule, **When** User B calls GET on the dataset detail, **Then** the backend returns 403.
2. **Given** a dataset owned by User A and a METADATA READ rule for Group X, **When** User B (member of Group X) calls the metadata proxy, **Then** the backend returns 403 (READ on METADATA does not grant access to the proxy).
3. **Given** a dataset owned by User A and a METADATA WRITE rule for Group X, **When** User B (member of Group X) calls the metadata proxy, **Then** the backend allows the action.
4. **Given** a dataset owned by User A, **When** User B (not the owner, not an admin) calls the rights editing endpoint, **Then** the backend returns 403.
5. **Given** a dataset owned by User A, **When** User B (not the owner, not an admin) calls an ingestion tunnel endpoint with the dataset identifier (reconfigure) or the delete endpoint, **Then** the backend returns 403.
6. **Given** a dataset owned by User A, **When** User A calls any endpoint on the dataset (including the metadata proxy), **Then** the backend allows the action.
7. **Given** any dataset, **When** an administrator calls any endpoint (including the metadata proxy), **Then** the backend allows the action.

---

### User Story 3 - Frontend Restricts Navigation for Users with Read-Only Access (Priority: P2)

When a user has only read access (METADATA READ) on a dataset, the frontend shows the dataset in the list but does not allow navigating to its detail pages (edit, events, authorizations). Clicking on the dataset in the list has no effect, or shows a visual indicator that the user can only view the list entry.

**Why this priority**: Preventing navigation to unauthorized pages avoids confusion and wasted time. However, this is secondary to backend enforcement.

**Independent Test**: A user with METADATA READ on a dataset sees it in the list but cannot navigate to its detail pages.

**Acceptance Scenarios**:

1. **Given** a dataset with METADATA READ for Group X, **When** User B (member of Group X) views the dataset list, **Then** the dataset is displayed but has no clickable navigation to detail pages.
2. **Given** a dataset with no permissions for User B's group, **When** User B views the dataset list, **Then** the dataset does not appear at all.

---

### User Story 4 - Frontend Allows Metadata Editing for Users with Write Access (Priority: P2)

When a user belongs to a group with METADATA WRITE on a dataset, the frontend allows them to navigate to the metadata editing page. Other actions or detail pages (authorizations, events, recurrence, reconfigure, delete) remain inaccessible.

**Why this priority**: This enables collaborators to edit metadata as intended by the owner who granted the permission.

**Independent Test**: A user with METADATA WRITE on a dataset can navigate to the metadata editing page but sees no action button to reconfigure, or delete. The links for authorizations, events, recurrence are disabled.

**Acceptance Scenarios**:

1. **Given** a dataset with METADATA WRITE for Group X, **When** User B (member of Group X) views the dataset list, **Then** the dataset is clickable and leads to the metadata editing page.
2. **Given** a dataset with METADATA WRITE for Group X, **When** User B (member of Group X) is on the dataset detail view, **Then** only the metadata editing page is accessible; sidebar actions and links for authorizations, events, recurrence planning, reconfigure, and delete are disabled.

---

### User Story 5 - Owner Has Full Access to All Actions (Priority: P2)

The owner of a dataset always has access to every action: viewing details, editing metadata, viewing and editing rights, viewing events and downloading logs, scheduling ingestion recurrence, reconfiguring, and deleting the dataset. All navigation links and actions are visible and functional for the owner.

**Why this priority**: The owner must always retain full control over their datasets.

**Independent Test**: The dataset owner can access all pages and perform all actions on their own dataset.

**Acceptance Scenarios**:

1. **Given** a dataset owned by User A, **When** User A navigates to the dataset, **Then** all sidebar links (edit metadata, authorizations, events, recurrence planning) are visible and functional.
2. **Given** a dataset owned by User A, **When** User A views the dataset, **Then** the reconfigure and delete actions are available.

---

### User Story 6 - Non-Owner Cannot Reconfigure or Delete (Priority: P3)

The reconfigure and delete actions on a dataset are reserved exclusively for the owner and administrators. Non-owners, even those with METADATA WRITE or DATA WRITE, cannot reconfigure or delete a dataset. The frontend hides these actions, and the backend rejects them with 403.

**Why this priority**: Reconfiguration and deletion are destructive or structurally impactful operations that should be restricted to the person who created the dataset.

**Independent Test**: A user with METADATA WRITE on a dataset cannot see the reconfigure or delete buttons and receives 403 if they attempt these actions via API.

**Acceptance Scenarios**:

1. **Given** a dataset owned by User A and METADATA WRITE for Group X, **When** User B (member of Group X) views the dataset detail, **Then** the reconfigure and delete options are not displayed.
2. **Given** a dataset owned by User A, **When** User B calls an ingestion tunnel endpoint with the dataset identifier (reconfigure) via API, **Then** the backend returns 403.
3. **Given** a dataset owned by User A, **When** User B calls the delete endpoint via API, **Then** the backend returns 403.

---

### Edge Cases

- What happens when a user's group changes while they are viewing a dataset? The backend rejects the next action if the new group lacks permissions; the frontend reflects the change on next page load or list refresh.
- What happens when the owner of a dataset is removed from the system? The dataset retains its owner field; only administrators can manage it.
- What happens when an administrator is also a member of a group with limited permissions? The administrator role takes precedence and grants full access.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dataset list endpoint MUST return only datasets where the current user is the owner, or where at least one METADATA permission rule (READ or WRITE) exists for the user's group. Administrators MUST see all datasets.
- **FR-002**: The backend MUST return HTTP 403 Forbidden when a user who is not the owner, not an administrator, and whose group has no matching permission rule attempts an unauthorized action on a dataset.
- **FR-003**: Viewing dataset details (navigating to a dataset page) MUST require at least METADATA WRITE permission for the user's group, or ownership, or administrator role.
- **FR-004**: Accessing the metadata proxy (which handles both reading and writing metadata via GeoNetwork) MUST require METADATA WRITE permission for the user's group, or ownership, or administrator role. There is no separate metadata read or edit endpoint; all metadata access goes through this proxy.
- **FR-005**: Editing rights (permissions rules) on a dataset MUST require ownership or administrator role.
- **FR-006**: Viewing events on a dataset MUST require ownership or administrator role.
- **FR-007**: Planning ingestion recurrence MUST require ownership or administrator role.
- **FR-008**: Reconfiguring a dataset MUST require ownership or administrator role. Reconfiguration uses the same ingestion tunnel endpoints as initial ingestion, called with the identifier of an existing dataset. There is no dedicated reconfiguration endpoint.
- **FR-009**: Deleting a dataset MUST require ownership or administrator role.
- **FR-010**: The frontend MUST NOT allow navigation to dataset detail pages when the user has only METADATA READ (or no permission) on the dataset.
- **FR-011**: The frontend MUST allow navigation only to the metadata editing page when the user has METADATA WRITE but is not the owner.
- **FR-012**: The frontend MUST hide the reconfigure and delete actions for users who are not the dataset owner or administrator.
- **FR-013**: If a user manually navigates to a page they are not authorized for via URL, the frontend MUST display the HTTP 403 error as returned by the backend. There is no frontend-specific redirect or custom handling for manual navigation to unauthorized pages.
- **FR-014**: The owner of a newly created dataset MUST have full access to all actions without any explicit permission rules being created.
- **FR-015**: WRITE permission MUST implicitly include READ permission (a user with WRITE can also perform actions that require READ).
- **FR-016**: Since all metadata reading and writing passes through the proxy (covered by FR-004), METADATA READ alone MUST NOT grant access to the proxy. METADATA READ only affects dataset list visibility (FR-001).

### Key Entities

- **IntegrityLink (Dataset)**: Represents the association between a metadata record and a data record. Has an owner and an organization. Central entity to which permission rules apply.
- **IntegrityLinkRule (Permission Rule)**: Grants a group a level of access (READ or WRITE) on a specific dimension (METADATA or DATA) of a dataset. Multiple rules can exist per dataset.
- **User**: Identified by username and group membership. Authenticated via gateway-injected headers. A user belongs to exactly one group.
- **Group/Role**: A named grouping of users. Permission rules reference groups, not individual users. Groups come from external systems (GeoNetwork for metadata groups, GeoServer for data groups).

## Assumptions

- The user's group membership is reliably provided by the gateway via request headers and is up-to-date at request time. Each user belongs to exactly one group.
- The ADMINISTRATOR role confers full access to all datasets and all actions, bypassing all permission checks.
- WRITE permission on METADATA is sufficient to navigate to and edit metadata. READ permission on METADATA is sufficient only to see the dataset in the list, not to navigate to any detail page.
- Permission rules for DATA (READ/WRITE) do not affect visibility in the dataset list or navigation to pages within DataKern; they control access to the underlying data in external systems.
- When no permission rules exist for a dataset (freshly created state), only the owner and administrators can access it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of unauthorized API calls to protected dataset endpoints return HTTP 403 Forbidden.
- **SC-002**: Users without any permission on a dataset never see it in the dataset list.
- **SC-003**: Users with only READ permission on metadata can see the dataset in the list but cannot navigate to any detail page.
- **SC-004**: Users with WRITE permission on metadata can access only the metadata editing page and no other detail page.
- **SC-005**: Only the dataset owner and administrators can access the authorizations, events, recurrence planning, reconfigure, and delete features.
- **SC-006**: The dataset owner can perform all actions on their own dataset without needing any explicit permission rule.
- **SC-007**: All permission checks are resolved within the normal request handling time, with no noticeable delay for the user.
