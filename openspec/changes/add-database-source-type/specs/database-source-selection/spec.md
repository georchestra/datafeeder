## ADDED Requirements

### Requirement: Database radio button visibility (P1)
The source selector component SHALL display a "Database" radio button option only when the platform has a database source connection configured. The frontend determines this by checking that `enabled_features` from `GET /settings` includes `"database_source"`.

#### Scenario: Database source is available
- **WHEN** the `GET /settings` response includes `"database_source"` in `enabled_features`
- **THEN** the source selector displays a "Database" radio button alongside the existing "File" and "FTP" options

#### Scenario: Database source is not configured
- **WHEN** the `GET /settings` response does NOT include `"database_source"` in `enabled_features`
- **THEN** the source selector does NOT display the "Database" radio button
- **AND** the UI behaves exactly as before (only File and FTP options)

#### Scenario: Settings endpoint fails
- **WHEN** the `GET /settings` request fails
- **THEN** the "Database" radio button is NOT displayed (safe default)

### Requirement: Database source form fields (P1)
When the user selects the "Database" radio button, the component SHALL display two text input fields: "Schema" and "Table". Both fields are mandatory. The file upload, URL input, and FTP fields SHALL be hidden.

#### Scenario: User selects database source type
- **WHEN** the user clicks the "Database" radio button
- **THEN** the file/URL/FTP input area is replaced by two text inputs: schema name and table name
- **AND** both fields are initially empty

#### Scenario: User switches from database to another source type
- **WHEN** the user has selected "Database" and entered schema/table values
- **AND** the user switches to "File" or "FTP"
- **THEN** the schema and table fields are cleared
- **AND** the appropriate input area for the new source type is shown

#### Scenario: User switches from another source type to database
- **WHEN** the user has selected "File" or "FTP" and entered data
- **AND** the user switches to "Database"
- **THEN** any file/URL/FTP data is cleared
- **AND** the schema and table input fields are shown empty

### Requirement: Schema and table validation (P1)
Both schema and table fields MUST be non-empty before the user can proceed to the next step. The wizard "Next" button SHALL be disabled when either field is empty.

#### Scenario: Both fields filled
- **WHEN** the user has entered a non-empty schema name and a non-empty table name
- **THEN** the "Next" button is enabled

#### Scenario: Schema field empty
- **WHEN** the table field has a value but the schema field is empty
- **THEN** the "Next" button is disabled

#### Scenario: Table field empty
- **WHEN** the schema field has a value but the table field is empty
- **THEN** the "Next" button is disabled

#### Scenario: Both fields empty
- **WHEN** both schema and table fields are empty
- **THEN** the "Next" button is disabled

#### Scenario: Whitespace-only values
- **WHEN** a field contains only whitespace characters
- **THEN** it SHALL be treated as empty (button disabled)

### Requirement: Database source submission (P1)
When the user submits a database source, the frontend SHALL send a multipart form request to `POST /ingestion/staging` (or `PUT /ingestion/staging/{id}` for re-edit) with `type=database`, `db_schema=<schema>`, and `db_table=<table>`.

#### Scenario: New database source submission
- **WHEN** the user completes the source selection step with type "Database", schema "public", and table "my_data"
- **THEN** the frontend sends `POST /ingestion/staging` with form fields `type=database`, `db_schema=public`, `db_table=my_data`

#### Scenario: Re-edit database source submission
- **WHEN** the user edits an existing database-sourced IntegrityLink and modifies schema/table
- **THEN** the frontend sends `PUT /ingestion/staging/{id}` with the updated `db_schema` and `db_table` values

### Requirement: User-friendly title from table name (P1)
For database sources, the default user-friendly title SHALL be the table name. This title is used in step 3 of the wizard and on the dashboard.

#### Scenario: Default title for database source
- **WHEN** the staging DAG succeeds for a database source with table name "cadastre_parcels"
- **AND** the user reaches step 3 (title & recurrence)
- **THEN** the title input is pre-filled with "cadastre_parcels"

#### Scenario: User overrides title
- **WHEN** the title is pre-filled with the table name
- **AND** the user modifies the title to "Parcelles cadastrales"
- **THEN** the custom title is used instead

### Requirement: Re-edit pre-fills database fields (P2)
When a user navigates back to edit an existing database-sourced import (via dashboard or back button), the schema and table fields SHALL be pre-filled with the previously saved values. The "Database" radio button SHALL be selected.

#### Scenario: Re-edit from dashboard
- **WHEN** the user clicks "Edit" on a database-sourced dataset from the dashboard
- **THEN** the source selector shows "Database" selected
- **AND** the schema field contains the previously saved schema name
- **AND** the table field contains the previously saved table name

#### Scenario: Re-edit when database feature becomes unavailable
- **WHEN** the user tries to edit a database-sourced dataset
- **AND** the `database_source` feature flag is no longer in `enabled_features`
- **THEN** the database radio button is still shown for this specific edit session (since the IntegrityLink already has type=database)
- **AND** the user can re-submit with the same or modified schema/table

### Requirement: Dashboard navigation rules preserved (P1)
Database-sourced datasets SHALL follow the same dashboard navigation rules as file/URL/FTP sources (as defined in GSMEL-944). The source type does not affect navigation behavior from step 2 onward.

#### Scenario: Database source on dashboard
- **WHEN** a database-sourced dataset appears on the dashboard
- **THEN** it follows the same navigation rules as any other source type
- **AND** the source type indicator shows "Database" (or equivalent label)

#### Scenario: Staging failure for database source
- **WHEN** the staging DAG fails for a database source (e.g., invalid schema/table)
- **THEN** the IntegrityLink is deleted via the failure callback
- **AND** the user can start a new import
