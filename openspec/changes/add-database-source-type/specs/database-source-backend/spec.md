## ADDED Requirements

### Requirement: Source database connection configuration (P1)
The backend SHALL support an optional external source database connection via environment variables: `POSTGRES_SOURCE_HOST`, `POSTGRES_SOURCE_PORT`, `POSTGRES_SOURCE_USER`, `POSTGRES_SOURCE_PASSWORD`, `POSTGRES_SOURCE_DB`. All fields default to `None`. When `POSTGRES_SOURCE_HOST` is set (non-null, non-empty), the database source feature is considered available.

#### Scenario: Source DB fully configured
- **WHEN** `POSTGRES_SOURCE_HOST`, `POSTGRES_SOURCE_PORT`, `POSTGRES_SOURCE_USER`, `POSTGRES_SOURCE_PASSWORD`, and `POSTGRES_SOURCE_DB` are all set
- **THEN** the database source feature is available

#### Scenario: Source DB not configured
- **WHEN** `POSTGRES_SOURCE_HOST` is not set or empty
- **THEN** the database source feature is not available
- **AND** `"database_source"` is NOT included in `enabled_features`

#### Scenario: Partial configuration
- **WHEN** `POSTGRES_SOURCE_HOST` is set but other `POSTGRES_SOURCE_*` fields are missing
- **THEN** the feature is still flagged as available (host presence is the gate)
- **AND** the missing fields will cause a connection error at staging DAG time (fail-fast)

### Requirement: Database source feature flag in settings (P1)
The `GET /settings` endpoint SHALL include `"database_source"` in the `enabled_features` array when the source database connection is configured.

#### Scenario: Feature flag present when configured
- **WHEN** `POSTGRES_SOURCE_HOST` is set to a non-empty value
- **THEN** `GET /settings` returns `enabled_features` containing `"database_source"`

#### Scenario: Feature flag absent when not configured
- **WHEN** `POSTGRES_SOURCE_HOST` is not set
- **THEN** `GET /settings` returns `enabled_features` without `"database_source"`

### Requirement: IntegrityLink model extension (P1)
The `integrity_link` table SHALL have two new nullable columns: `source_db_schema` (VARCHAR 63) and `source_db_table` (VARCHAR 63). These are populated only when `source_import_type = 'database'`.

#### Scenario: Database source IntegrityLink creation
- **WHEN** a staging request with `type=database`, `db_schema=cadastre`, `db_table=parcels` is submitted
- **THEN** the created IntegrityLink has `source_db_schema='cadastre'` and `source_db_table='parcels'`
- **AND** `source_import_type='database'`

#### Scenario: Non-database source IntegrityLink
- **WHEN** a staging request with `type=file` is submitted
- **THEN** the IntegrityLink has `source_db_schema=NULL` and `source_db_table=NULL`

### Requirement: Schema and table input validation (P1)
The backend SHALL validate `db_schema` and `db_table` fields to prevent SQL injection. Both MUST match the pattern `^[a-z][a-z0-9_]{0,62}$` (lowercase letter start, alphanumeric + underscores, max 63 chars). Invalid values SHALL return HTTP 422.

#### Scenario: Valid schema and table
- **WHEN** `db_schema=public` and `db_table=my_data_table`
- **THEN** the request is accepted

#### Scenario: Schema with uppercase
- **WHEN** `db_schema=Public`
- **THEN** the backend returns HTTP 422 with a validation error

#### Scenario: Table starting with number
- **WHEN** `db_table=123table`
- **THEN** the backend returns HTTP 422 with a validation error

#### Scenario: Schema with special characters
- **WHEN** `db_schema=my-schema` (contains hyphen)
- **THEN** the backend returns HTTP 422 with a validation error

#### Scenario: Empty schema or table
- **WHEN** `type=database` and `db_schema` or `db_table` is missing or empty
- **THEN** the backend returns HTTP 400 with detail "Schema and table are required for database import type"

### Requirement: Staging endpoint handles database source type (P1)
The `POST /ingestion/staging` and `PUT /ingestion/staging/{id}` endpoints SHALL accept `type=database` with `db_schema` and `db_table` form fields. The endpoint SHALL create/update an IntegrityLink with the database-specific fields, generate a staging table name, and trigger the staging DAG with `source_type=DATABASE`.

#### Scenario: New database source staging
- **WHEN** `POST /ingestion/staging` is called with `type=database`, `db_schema=geo`, `db_table=rivers`
- **THEN** an IntegrityLink is created with `source_import_type=database`, `source_db_schema=geo`, `source_db_table=rivers`
- **AND** `source_url` is set to `db://geo/rivers` (informational)
- **AND** `source_file_name` is set to `rivers` (for title fallback)
- **AND** `source_file_type` is NULL
- **AND** the staging DAG is triggered with `source_type=DATABASE`

#### Scenario: Edit database source staging
- **WHEN** `PUT /ingestion/staging/{id}` is called with `type=database`, `db_schema=geo`, `db_table=lakes`
- **THEN** the existing IntegrityLink is updated with the new schema and table
- **AND** the old staging table is dropped
- **AND** a new staging DAG is triggered

#### Scenario: Switch from file to database on edit
- **WHEN** an IntegrityLink was created with `type=file`
- **AND** `PUT /ingestion/staging/{id}` is called with `type=database`, `db_schema=geo`, `db_table=roads`
- **THEN** the IntegrityLink is updated to `source_import_type=database`
- **AND** `source_db_schema` and `source_db_table` are set
- **AND** file-specific fields (`source_file_type`) are cleared

#### Scenario: Switch from database to file on edit
- **WHEN** an IntegrityLink was created with `type=database`
- **AND** `PUT /ingestion/staging/{id}` is called with `type=file` and a file upload
- **THEN** the IntegrityLink is updated to `source_import_type=file`
- **AND** `source_db_schema` and `source_db_table` are set to NULL

### Requirement: No authentication encryption for database source (P1)
The database source type SHALL NOT use per-import credential encryption. The source DB credentials are platform-level configuration (env vars / k8s secrets), not user-provided.

#### Scenario: Database source has no encrypted credentials
- **WHEN** a database source staging request is submitted
- **THEN** `source_username` and `source_password_encrypted` are NULL on the IntegrityLink
- **AND** no credential encryption is attempted

### Requirement: Staging metadata title fallback for database source (P1)
The `GET /ingestion/staging/{id}/metadata` endpoint SHALL return the table name as the default title for database sources when no custom title has been set.

#### Scenario: Default title from table name
- **WHEN** `GET /ingestion/staging/{id}/metadata` is called for a database-sourced IntegrityLink with `source_db_table=parcels`
- **AND** no custom `integrity_title` has been set
- **THEN** the response `title` field is `"parcels"`

#### Scenario: Custom title overrides table name
- **WHEN** a database-sourced IntegrityLink has `integrity_title="Parcelles cadastrales"`
- **THEN** the response `title` field is `"Parcelles cadastrales"`

### Requirement: Database migration (P1)
An Alembic migration SHALL add `source_db_schema` and `source_db_table` columns to the `integrity_link` table. The migration MUST be backwards-compatible (nullable columns, no data backfill).

#### Scenario: Migration applies cleanly
- **WHEN** the Alembic migration runs on an existing database with IntegrityLink data
- **THEN** the two new columns are added with NULL values for all existing rows
- **AND** existing data is not modified

#### Scenario: Migration rollback
- **WHEN** the migration is rolled back
- **THEN** the two columns are dropped
- **AND** no data loss occurs for other columns

### Requirement: Dev environment seed data (P2)
The development environment SHALL include a SQL seed script that creates a source schema with at least one table containing fake geospatial data, and the `POSTGRES_SOURCE_*` env vars SHALL be configured in docker-compose to point to this data.

#### Scenario: Developer starts fresh environment
- **WHEN** a developer runs `docker-compose up`
- **THEN** the source database schema is created with seed data
- **AND** `POSTGRES_SOURCE_*` env vars are set
- **AND** `GET /settings` includes `"database_source"` in `enabled_features`
