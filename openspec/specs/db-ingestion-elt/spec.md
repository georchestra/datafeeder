## Purpose

Airflow task and data_manipulation function to copy a table from an external PostgreSQL database into the staging schema. Includes Airflow connection configuration and the ingestion function.

## Requirements

### Requirement: Airflow connection SOURCE_DB_1 (P1)
The `conn.json` file SHALL contain a `SOURCE_DB_1` entry with the connection URI to the external database. The DAG `utils.py` module SHALL expose a `get_source_sql_engine(db_key: str)` function that returns a `SQLAlchemy Engine` via `PostgresHook(db_key)`. The Airflow connection key SHALL match the key in the backend's `SOURCE_DATABASES` dictionary.

#### Scenario: SOURCE_DB_1 connection available
- **WHEN** `conn.json` contains the `SOURCE_DB_1` entry with a valid PostgreSQL URI
- **THEN** `get_source_sql_engine("SOURCE_DB_1")` returns an `Engine` connected to the source database

#### Scenario: SOURCE_DB_1 connection missing
- **WHEN** `conn.json` does not contain the `SOURCE_DB_1` entry
- **THEN** `get_source_sql_engine("SOURCE_DB_1")` raises an Airflow exception

### Requirement: ingest_data_from_database_into_postgis function (P1)
The module `libs/data_manipulation/src/data_manipulation/ingestion.py` SHALL expose a function `ingest_data_from_database_into_postgis(source_schema, source_table, source_engine, target_table, target_engine, target_schema)` that reads a table from the source database and writes it into the data database's staging schema via `write_data_to_postgis()`.

#### Scenario: Non-geographic table ingestion
- **WHEN** the source table `public.communes` exists in the source database and has no geometry column
- **THEN** the function reads the table with `pd.read_sql(select(table), source_engine)` (via SQLAlchemy `autoload_with`)
- **AND** writes data into `staging.{target_table}` via `write_data_to_postgis()`
- **AND** data is identical to the source

#### Scenario: Geographic table ingestion
- **WHEN** the source table `geo.rivers` exists in the source database and contains a geometry column
- **THEN** the function reads the table with `gpd.read_postgis()`
- **AND** writes data into `staging.{target_table}` via `write_data_to_postgis()`
- **AND** geometry is preserved

#### Scenario: Non-existent source table
- **WHEN** the source table `public.nonexistent` does not exist in the source database
- **THEN** the function raises an exception

#### Scenario: Non-existent source schema
- **WHEN** the source schema `nonexistent` does not exist in the source database
- **THEN** the function raises an exception

### Requirement: Airflow database_ingest_step task (P1)
The `ingestion` task group SHALL include a `"DATABASE"` case in the branching that calls `ingest_data_from_database_into_postgis()`. The task SHALL parse the `source` parameter (format `db://{db_key}/{schema}/{table}`) to extract the database key, schema, and source table.

#### Scenario: Branching to database_ingest_step
- **WHEN** the staging DAG is triggered with `source_type=DATABASE` and `source=db://SOURCE_DB_1/geo/rivers`
- **THEN** the branching selects `database_ingest_step`
- **AND** the task parses `source` to extract `db_key=SOURCE_DB_1`, `schema=geo`, and `table=rivers`
- **AND** the task calls `ingest_data_from_database_into_postgis()` with `source_engine` from `get_source_sql_engine("SOURCE_DB_1")` and `target_engine` from `get_data_sql_engine()`
- **AND** the table is copied into `staging.{staging_table_name}`

#### Scenario: Staging table name from params
- **WHEN** the DAG is triggered with `staging_table_name` in params
- **THEN** the task uses that name as the target table in staging

#### Scenario: Staging table name from XCom (recurrence)
- **WHEN** the process DAG is in refresh mode with `source_type=DATABASE`
- **AND** `staging_table_name` is not in params
- **THEN** the task retrieves the name from XCom (`generate_staging_table_name`)

#### Scenario: Malformed source URL
- **WHEN** the `source` parameter does not start with `db://` or does not contain exactly 3 segments (`db_key`, `schema`, `table`)
- **THEN** the task raises an `AirflowException`

#### Scenario: Source URL with empty components
- **WHEN** the `source` parameter matches the format but any component (`db_key`, `schema`, `table`) is empty
- **THEN** the task raises an `AirflowException`

### Requirement: End-to-end pipeline identical to other sources (P1)
After `database_ingest_step` writes to staging, the rest of the pipeline (transformation, final write, callbacks) SHALL execute exactly as for other source types (FILE, URL, FTP). No post-staging pipeline changes are required.

#### Scenario: Transformation after database ingestion
- **WHEN** data from a database table has been ingested into staging
- **AND** the process DAG is triggered with an `IntegrityTransformation`
- **THEN** transformations are applied (rename, cast, filter, projection)
- **AND** transformed data is written to the final schema
- **AND** the staging table is cleaned up

#### Scenario: Data preview after database ingestion
- **WHEN** data from a database table has been ingested into staging
- **THEN** the `GET /ingestion/staging/{id}/preview` endpoint returns a data preview
- **AND** the `GET /ingestion/staging/{id}/metadata` endpoint returns metadata (columns, row_count)

#### Scenario: Recurrence with database source
- **WHEN** a dataset with `source_import_type=DATABASE` has a schedule configured
- **AND** the process DAG is triggered in refresh mode
- **THEN** Airflow re-ingests from the source database into a new staging table
- **AND** the transformation pipeline executes normally
