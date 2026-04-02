## ADDED Requirements

### Requirement: Dataset deletion by the owner

An authenticated user SHALL be able to delete a dataset they own from their data dashboard.

#### Scenario: Successful deletion by the owner

- **WHEN** a user sends `DELETE /api/ingestion/integrity-link/{id}` for a dataset they own
- **THEN** the system returns HTTP 204
- **THEN** the dataset is no longer accessible via `GET /api/ingestion/integrity-links/`

#### Scenario: Deletion refused for a non-owner

- **WHEN** a user sends `DELETE /api/ingestion/integrity-link/{id}` for a dataset they do not own
- **THEN** the system returns HTTP 403

#### Scenario: Non-existent dataset

- **WHEN** a user sends `DELETE /api/ingestion/integrity-link/{id}` with an unknown identifier
- **THEN** the system returns HTTP 404

### Requirement: Deletion by an administrator

An administrator SHALL be able to delete any dataset regardless of who owns it.

#### Scenario: Admin deletes a dataset belonging to another user

- **WHEN** an administrator sends `DELETE /api/ingestion/integrity-link/{id}` for a dataset belonging to another user
- **THEN** the system returns HTTP 204
- **THEN** the dataset is no longer accessible

### Requirement: Associated resource cleanup on deletion

When a dataset is deleted, the system SHALL clean up all associated resources in the following order: Airflow DAG (if recurrence), GeoServer layer, final data table, staging table (best-effort, to capture orphans from failed ingestions), GeoNetwork record, IntegrityLink record (with cascade on IntegrityLinkRule).

#### Scenario: Full deletion of a dataset with recurrence

- **WHEN** a dataset with a defined `schedule` is deleted
- **THEN** the corresponding Airflow DAG is deleted
- **THEN** the GeoServer layer is deleted
- **THEN** the final data table is deleted
- **THEN** the staging table is deleted (best-effort — `DROP TABLE IF EXISTS`)
- **THEN** the GeoNetwork record is deleted
- **THEN** the IntegrityLink record is deleted from the database
- **THEN** the associated IntegrityLinkRules are deleted by cascade

#### Scenario: Deletion of a dataset without recurrence

- **WHEN** a dataset without a `schedule` is deleted
- **THEN** no Airflow operation is attempted
- **THEN** the other resources (GeoServer, data table, staging table, GeoNetwork, IntegrityLink) are deleted

#### Scenario: GeoServer or GeoNetwork resource not found

- **WHEN** a GeoServer or GeoNetwork resource is not found during deletion
- **THEN** the error is ignored (best-effort) and deletion continues

### Requirement: Blocked on Airflow DAG deletion failure

If the Airflow DAG deletion fails (excluding 404), the system SHALL return an error and interrupt the cleanup.

#### Scenario: DAG deletion failure

- **WHEN** the Airflow DAG deletion returns an error other than 404
- **THEN** the backend returns HTTP 500
- **THEN** no other resource is deleted
- **THEN** the dataset remains in the list

#### Scenario: Airflow DAG not found (no DAG created)

- **WHEN** the DAG deletion returns 404 (the DAG does not exist in Airflow)
- **THEN** the error is ignored and cleanup continues normally

### Requirement: Delete icon displayed on row hover

In the data dashboard, the delete icon (trash) SHALL appear only when hovering over the corresponding row.

#### Scenario: Row hover

- **WHEN** the user hovers over a dashboard row
- **THEN** a trash icon appears on the right side of the row

#### Scenario: End of hover

- **WHEN** the cursor leaves the row
- **THEN** the trash icon disappears

### Requirement: Dataset removed from list after deletion

After a successful deletion, the dataset SHALL disappear immediately from the list without a full page reload.

#### Scenario: Deletion confirmed by the user

- **WHEN** the user clicks the delete icon
- **THEN** a confirmation dialog is displayed
- **WHEN** the user confirms deletion and the DELETE request returns HTTP 204
- **THEN** the corresponding row is removed from the displayed list
- **THEN** the remaining list is unchanged

#### Scenario: Deletion cancelled by the user

- **WHEN** the user clicks the delete icon
- **THEN** a confirmation dialog is displayed
- **WHEN** the user cancels
- **THEN** no DELETE request is sent
- **THEN** the row remains in the list

#### Scenario: Backend deletion failure

- **WHEN** the user confirms deletion and the DELETE request returns an error (HTTP 4xx or 5xx)
- **THEN** an error toast is displayed with the message "Deletion encountered an error"
- **THEN** the row remains in the list
- **THEN** the delete icon becomes interactive again
