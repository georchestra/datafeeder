## Purpose

Backend handling of the database source type — configuration, feature flag exposure, staging endpoint support, IntegrityLink persistence of schema/table via `source_url`, and Airflow DAG triggering with source type DATABASE.

## Requirements

### Requirement: Source database connection configuration (P1)
The backend SHALL support a `SOURCE_DATABASES` dictionary of type `dict[str, PostgresDsn]` in `Settings`, where each key is a logical identifier and each value is a PostgreSQL connection URI validated by Pydantic (`PostgresDsn`). The dictionary is provided as a JSON string via environment variable. In v1, a single entry is used (`SOURCE_DB_1`). The database source feature is considered available when `SOURCE_DATABASES` contains at least one entry.

The variables `POSTGRES_SOURCE_HOST`, `POSTGRES_SOURCE_PORT`, `POSTGRES_SOURCE_USER`, `POSTGRES_SOURCE_PASSWORD`, `POSTGRES_SOURCE_DB` are removed and replaced by `SOURCE_DATABASES`.

#### Scenario: SOURCE_DATABASES configured with one entry
- **WHEN** `SOURCE_DATABASES='{"SOURCE_DB_1": "postgresql://user:pass@host:5432/db"}'`
- **THEN** the database source feature is available
- **AND** `"database_source"` is included in `enabled_features`

#### Scenario: SOURCE_DATABASES empty or missing
- **WHEN** `SOURCE_DATABASES` is not set or is an empty dictionary `{}`
- **THEN** the database source feature is not available
- **AND** `"database_source"` is NOT included in `enabled_features`

#### Scenario: SOURCE_DATABASES with multiple entries (future-proof)
- **WHEN** `SOURCE_DATABASES='{"SOURCE_DB_1": "postgresql://...", "SOURCE_DB_2": "postgresql://..."}'`
- **THEN** the database source feature is available
- **AND** in v1, only the first entry is used implicitly

### Requirement: Database source feature flag in settings (P1)
The `GET /settings` endpoint SHALL include `"database_source"` in the `enabled_features` array when `SOURCE_DATABASES` contains at least one non-empty entry.

#### Scenario: Feature flag present when SOURCE_DATABASES configured
- **WHEN** `SOURCE_DATABASES` contains at least one entry with a non-empty URI
- **THEN** `GET /settings` returns `enabled_features` containing `"database_source"`

#### Scenario: Feature flag absent when SOURCE_DATABASES empty
- **WHEN** `SOURCE_DATABASES` is empty or not set
- **THEN** `GET /settings` returns `enabled_features` without `"database_source"`

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
The `POST /ingestion/staging` and `PUT /ingestion/staging/{id}` endpoints SHALL accept `type=database` with `db_schema` and `db_table` form fields. The `source_url` is encoded as `db://{db_key}/{schema}/{table}`. In v1, the database key is the first (and only) key from the `SOURCE_DATABASES` dictionary. No new IntegrityLink columns are added.

#### Scenario: New database source staging
- **WHEN** `POST /ingestion/staging` is called with `type=database`, `db_schema=geo`, `db_table=rivers`
- **AND** `SOURCE_DATABASES` contains `SOURCE_DB_1`
- **THEN** an IntegrityLink is created with `source_import_type=database`
- **AND** `source_url` is set to `db://SOURCE_DB_1/geo/rivers`
- **AND** `source_file_name` is NULL
- **AND** `source_file_type` is NULL
- **AND** `source_username` and `source_password_encrypted` are NULL
- **AND** the staging DAG is triggered with `source_type=DATABASE`

#### Scenario: Edit database source staging
- **WHEN** `PUT /ingestion/staging/{id}` is called with `type=database`, `db_schema=geo`, `db_table=lakes`
- **THEN** the existing IntegrityLink is updated with `source_url=db://SOURCE_DB_1/geo/lakes`
- **AND** the old staging table is dropped
- **AND** a new staging DAG is triggered

#### Scenario: Switch from file to database on edit
- **WHEN** an IntegrityLink was created with `type=file`
- **AND** `PUT /ingestion/staging/{id}` is called with `type=database`, `db_schema=geo`, `db_table=roads`
- **THEN** the IntegrityLink is updated to `source_import_type=database`
- **AND** `source_url` is set to `db://SOURCE_DB_1/geo/roads`
- **AND** `source_file_type` is cleared

#### Scenario: Switch from database to file on edit
- **WHEN** an IntegrityLink was created with `type=database`
- **AND** `PUT /ingestion/staging/{id}` is called with `type=file` and a file upload
- **THEN** the IntegrityLink is updated to `source_import_type=file`
- **AND** `source_url` is set to the uploaded file path

### Requirement: No authentication encryption for database source (P1)
The database source type SHALL NOT use per-import credential encryption. The source DB credentials are platform-level configuration (env vars / k8s secrets), not user-provided.

#### Scenario: Database source has no encrypted credentials
- **WHEN** a database source staging request is submitted
- **THEN** `source_username` and `source_password_encrypted` are NULL on the IntegrityLink
- **AND** no credential encryption is attempted

### Requirement: Guard temp file deletion for database sources (P1)
The `dag_success_callback` SHALL NOT call `delete_temp_file` when the IntegrityLink's `source_import_type` is `DATABASE`. Database sources store `db://{db_key}/{schema}/{table}` in `source_url`, which is not a file path.

#### Scenario: Database source staging succeeds
- **WHEN** `dag_success_callback` is called for a database-sourced IntegrityLink
- **THEN** `delete_temp_file` is NOT called
- **AND** no file deletion error is logged

#### Scenario: File source staging succeeds
- **WHEN** `dag_success_callback` is called for a file-sourced IntegrityLink
- **THEN** `delete_temp_file` IS called with `source_url` (existing behavior unchanged)

### Requirement: Staging metadata title fallback for database source (P1)
The `GET /ingestion/staging/{id}/metadata` endpoint SHALL return the table name as the default title for database sources when no custom title has been set. The table name is parsed from `source_url` (`db://{db_key}/{schema}/{table}`).

#### Scenario: Default title from table name
- **WHEN** `GET /ingestion/staging/{id}/metadata` is called for a database-sourced IntegrityLink with `source_url=db://SOURCE_DB_1/geo/parcels`
- **AND** no custom `integrity_title` has been set
- **AND** `source_file_name` is NULL
- **THEN** the response `title` field is `"parcels"`

#### Scenario: Custom title overrides table name
- **WHEN** a database-sourced IntegrityLink has `integrity_title="Parcelles cadastrales"`
- **THEN** the response `title` field is `"Parcelles cadastrales"`

### Requirement: Dev environment seed data (P2)
The development environment SHALL include a SQL seed script that creates a source schema with at least one table containing fake geospatial data, and `SOURCE_DATABASES` SHALL be configured in docker-compose to point to this data.

#### Scenario: Developer starts fresh environment
- **WHEN** a developer runs `docker-compose up`
- **THEN** the source database schema is created with seed data
- **AND** `SOURCE_DATABASES` is configured with at least one entry (e.g., `SOURCE_DB_1`)
- **AND** `GET /settings` includes `"database_source"` in `enabled_features`
