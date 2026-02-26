## ADDED Requirements

### Requirement: Dataset list visibility filtering
The dataset list endpoint SHALL return only datasets where the current user is the owner, or where at least one METADATA permission rule (READ or WRITE) exists for the user's group. Administrators SHALL see all datasets.

#### Scenario: User sees datasets with METADATA READ permission
- **WHEN** a user whose group has METADATA READ on a dataset views the dataset list
- **THEN** the dataset appears in the list

#### Scenario: User sees datasets with METADATA WRITE permission
- **WHEN** a user whose group has METADATA WRITE on a dataset views the dataset list
- **THEN** the dataset appears in the list

#### Scenario: User does not see datasets without permission
- **WHEN** a user whose group has no permission rule on a dataset views the dataset list
- **THEN** the dataset does not appear in the list

#### Scenario: Owner always sees own datasets
- **WHEN** the dataset owner views the dataset list
- **THEN** the dataset always appears regardless of permission rules

#### Scenario: Administrator sees all datasets
- **WHEN** an administrator views the dataset list
- **THEN** all datasets appear

### Requirement: Backend rejects unauthorized dataset detail access
The backend SHALL return HTTP 403 Forbidden when a user who is not the owner, not an administrator, and whose group has no METADATA WRITE permission attempts to view dataset details.

#### Scenario: User without permission denied dataset details
- **WHEN** a user with no permission rule calls GET on the dataset detail
- **THEN** the backend returns 403

#### Scenario: User with METADATA READ denied dataset details
- **WHEN** a user with only METADATA READ calls GET on the dataset detail
- **THEN** the backend returns 403

#### Scenario: User with METADATA WRITE allowed dataset details
- **WHEN** a user with METADATA WRITE calls GET on the dataset detail
- **THEN** the backend allows the action

### Requirement: Backend rejects unauthorized metadata proxy access
Accessing the metadata proxy (which handles both reading and writing metadata via GeoNetwork) SHALL require METADATA WRITE permission for the user's group, or ownership, or administrator role. METADATA READ alone SHALL NOT grant access to the proxy.

#### Scenario: User with METADATA READ denied proxy access
- **WHEN** a user with only METADATA READ calls the metadata proxy
- **THEN** the backend returns 403

#### Scenario: User with METADATA WRITE allowed proxy access
- **WHEN** a user with METADATA WRITE calls the metadata proxy
- **THEN** the backend allows the action

#### Scenario: Owner allowed proxy access
- **WHEN** the dataset owner calls the metadata proxy
- **THEN** the backend allows the action

### Requirement: Backend rejects unauthorized rights editing
Editing rights (permission rules) on a dataset SHALL require ownership or administrator role.

#### Scenario: Non-owner denied rights editing
- **WHEN** a user who is not the owner and not an administrator calls the rights editing endpoint
- **THEN** the backend returns 403

#### Scenario: Owner allowed rights editing
- **WHEN** the dataset owner calls the rights editing endpoint
- **THEN** the backend allows the action

### Requirement: Backend rejects unauthorized events access
Viewing events on a dataset SHALL require ownership or administrator role.

#### Scenario: Non-owner denied events access
- **WHEN** a user who is not the owner and not an administrator calls the events endpoint
- **THEN** the backend returns 403

### Requirement: Backend rejects unauthorized recurrence planning
Planning ingestion recurrence SHALL require ownership or administrator role.

#### Scenario: Non-owner denied recurrence planning
- **WHEN** a user who is not the owner and not an administrator calls the recurrence planning endpoint
- **THEN** the backend returns 403

### Requirement: Backend rejects unauthorized reconfiguration
Reconfiguring a dataset SHALL require ownership or administrator role. Reconfiguration uses the same ingestion tunnel endpoints as initial ingestion, called with an existing dataset identifier.

#### Scenario: Non-owner denied reconfiguration
- **WHEN** a non-owner calls an ingestion tunnel endpoint with an existing dataset identifier
- **THEN** the backend returns 403

### Requirement: Backend rejects unauthorized deletion
Deleting a dataset SHALL require ownership or administrator role.

#### Scenario: Non-owner denied deletion
- **WHEN** a non-owner calls the delete endpoint
- **THEN** the backend returns 403

### Requirement: Owner full access
The dataset owner SHALL always have access to every action on their own dataset without needing any explicit permission rule: viewing details, editing metadata, viewing and editing rights, viewing events, scheduling recurrence, reconfiguring, and deleting.

#### Scenario: Owner performs any action
- **WHEN** the dataset owner calls any endpoint on their dataset
- **THEN** the backend allows the action

### Requirement: Administrator full access
Administrators SHALL have full access to all datasets and all actions, bypassing all permission checks.

#### Scenario: Administrator performs any action on any dataset
- **WHEN** an administrator calls any endpoint on any dataset
- **THEN** the backend allows the action

### Requirement: Frontend read-only navigation restriction
The frontend SHALL NOT allow navigation to dataset detail pages when the user has only METADATA READ (or no permission) on the dataset. The dataset SHALL appear in the list but SHALL NOT be clickable for navigation.

#### Scenario: Read-only user cannot navigate to details
- **WHEN** a user with only METADATA READ views the dataset list
- **THEN** the dataset is displayed but has no clickable navigation to detail pages

### Requirement: Frontend write-access navigation
The frontend SHALL allow navigation only to the metadata editing page when the user has METADATA WRITE but is not the owner. Sidebar actions for authorizations, events, recurrence, reconfigure, and delete SHALL be disabled.

#### Scenario: Write user navigates to metadata page only
- **WHEN** a user with METADATA WRITE clicks the dataset in the list
- **THEN** they are navigated to the metadata editing page

#### Scenario: Write user sees disabled sidebar actions
- **WHEN** a user with METADATA WRITE views the dataset detail
- **THEN** sidebar links for authorizations, events, recurrence, reconfigure, and delete are disabled

### Requirement: Frontend hides destructive actions for non-owners
The frontend SHALL hide the reconfigure and delete actions for users who are not the dataset owner or administrator.

#### Scenario: Non-owner does not see reconfigure and delete
- **WHEN** a non-owner views the dataset detail
- **THEN** reconfigure and delete options are not displayed

### Requirement: Frontend displays backend 403 errors
If a user manually navigates to a page they are not authorized for via URL, the frontend SHALL display the HTTP 403 error as returned by the backend. There is no frontend-specific redirect or custom handling.

#### Scenario: Manual URL navigation to unauthorized page
- **WHEN** a user manually enters the URL of an unauthorized dataset page
- **THEN** the frontend displays the 403 error from the backend
