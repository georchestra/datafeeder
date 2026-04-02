## Purpose

Configuration changes to move from a single source connection (`POSTGRES_SOURCE_*`) to an extensible `SOURCE_DATABASES` dictionary.

## MODIFIED Requirements

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

### Requirement: Staging endpoint source_url format (P1)
The `POST /ingestion/staging` and `PUT /ingestion/staging/{id}` endpoints SHALL build the `source_url` as `db://{db_key}/{schema}/{table}` when `type=database`. In v1, the database key is the first (and only) key from the `SOURCE_DATABASES` dictionary.

#### Scenario: source_url construction with database key
- **WHEN** `POST /ingestion/staging` is called with `type=database`, `db_schema=geo`, `db_table=rivers`
- **AND** `SOURCE_DATABASES` contains `SOURCE_DB_1`
- **THEN** `source_url` is set to `db://SOURCE_DB_1/geo/rivers`

#### Scenario: Title fallback for DATABASE source
- **WHEN** `integrity_title` is NULL and `source_url` is `db://SOURCE_DB_1/geo/rivers`
- **THEN** the displayed title is `rivers` (table name extracted from source_url)
