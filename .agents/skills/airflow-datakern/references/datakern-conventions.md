# DataKern Project Conventions

Project-specific rules, naming conventions, and integration patterns for DataKern Airflow DAGs.

## File Organization

```
apps/elt/dags/
├── callback.py               # HTTP callback utilities
├── models.py                 # Pydantic models (SourceType, etc.)
├── utils.py                  # Database hooks, engines, schema getters
├── staging_dag.py            # Initial data ingestion to staging
├── process_dag.py            # Transform staging → final table
├── process-dag-generator.py  # Dynamic DAGs from integrity_link
└── task_groups/
    ├── __init__.py
    ├── ingestion.py          # Reusable ingestion task groups
    └── transformation.py     # Reusable transformation task groups
```

### File Purposes

- **{purpose}_dag.py**: Main DAG definitions
- **{purpose}-dag-generator.py**: Dynamic DAG generation from DB
- **callback.py**: Reusable callback functions for external APIs
- **models.py**: Type definitions (`SourceType = Literal["FILE", "URL"]`)
- **utils.py**: Database connection utilities
- **task_groups/{purpose}.py**: Reusable task group factories

## Naming Conventions

### Files and DAGs
- **DAG files**: `{purpose}_dag.py` (e.g., `staging_dag.py`, `process_dag.py`)
- **DAG IDs**: `{purpose}_dag` (e.g., `staging_dag`, `process_dag`)
- **Dynamic DAG IDs**: `ingestion_{integrity_link_id}`
- **Generator files**: `{purpose}-dag-generator.py`

### Tasks and Groups
- **Task IDs**: `{action}_step` (e.g., `file_ingest_step`, `transform_step`)
- **Task IDs alternative**: `{purpose}_task` (e.g., `read_transform_write_task`)
- **Task group IDs**: `{purpose}_{mode}` (e.g., `initial_ingestion`, `refresh_ingestion`)
- **Branch task IDs**: `decide_{purpose}` (e.g., `decide_ingestion_mode`)

### Functions
- **Callback functions**: `_dag_{success|failure}_callback` (leading underscore)
- **Utility functions**: `get_{resource}_hook()`, `get_{resource}_engine()`
- **Factory functions**: `{name}_group(group_id: Literal[...])` returns `@task_group`
- **Internal task group impl**: `_impl()` or `_{name}_impl()`

### Parameters
Standard parameter naming across DAGs:

**Tables:**
- `staging_table_name`: Name of staging table
- `final_table_name`: Name of final/target table

**Source:**
- `source`: File path or URL
- `source_url`: Explicitly a URL (in integrity_link)
- `source_type`: Type enum (`"FILE"`, `"URL"`, `"OGC_WFS"`, `"FTP"`)
- `source_import_type`: Alternative name in some tables

**Authentication:**
- `basic_auth_encrypted`: Encrypted credentials (base64-encoded pgp_sym_encrypt)
- `source_auth_enabled`: Boolean flag
- `source_password_encrypted`: Alternative name

**Callbacks:**
- `success_callback_url`: URL to POST on success
- `failure_callback_url`: URL to POST on failure

**Configuration:**
- `integrity_transformation`: JSON config for data transformations
- `config_json`: Generic configuration object

**Scheduling:**
- `schedule`: Cron expression or Airflow schedule
- `schedule_enabled`: Boolean to enable/disable

## DataKern Database Integration

### Main Table: `datakern.integrity_link`

Links staging tables, final tables, and metadata together:

```sql
datakern.integrity_link:
  - id (uuid)
  - data_id (layer ID in GeoServer)
  - metadata_id (metadata ID in GeoNetwork)
  - integrity_title (human-readable title)
  - staging_table_name (staging schema table)
  - final_table_name (final schema table)
  - schedule (cron expression)
  - schedule_enabled (boolean)
  - integrity_transformation (jsonb config)
  - source_url (data source URL/path)
  - source_import_type (FILE|URL|etc.)
  - source_password_encrypted (encrypted auth)
  - source_auth_enabled (boolean)
  - staging_retrieve_time (time for staging ingestion)
  - last_retrieval_timestamp (last successful run)
  - integrity_owner (user who created)
  - integrity_organization (organization)
```

### Dynamic DAG Generation

Query for scheduled ingestions:

```python
sql = """
    SELECT 
        id::text,
        data_id,
        metadata_id,
        integrity_title,
        staging_table_name,
        final_table_name,
        schedule,
        schedule_enabled,
        integrity_transformation,
        source_url,
        source_import_type,
        source_password_encrypted,
        source_auth_enabled
    FROM datakern.integrity_link
    WHERE schedule_enabled = true
"""
```

For each row, generate a DAG: `ingestion_{id}`

### Schema Organization

**Staging schema (`staging`):**
- Temporary tables for initial ingestion
- Tables may be dropped after transformation
- Naming: `{uuid}` or `temp_{short_uuid}`

**Final schema (`data` or Variable `final_schema`):**
- Production tables with transformed data
- Naming: sanitized from `integrity_title`
- Include GeoServer-compatible naming (lowercase, underscores)

## Data Manipulation Library Integration

### Logging Configuration

Always configure logging at module level:

```python
import logging
from data_manipulation.logging import configure_logging

logger = logging.getLogger(__name__)
configure_logging(logger)
```

### Data Operations

Import from `data_manipulation`:

```python
from data_manipulation import (
    IntegrityTransformation,
    apply_transformations,
    read_data_from_postgis,
    write_data_to_postgis,
)
from data_manipulation.ingestion import (
    ingest_data_from_file_into_postgis,
    ingest_data_from_url_into_postgis,
)
from data_manipulation.encryption import decrypt_credentials
```

**Common patterns:**

```python
# Reading from PostGIS
data = read_data_from_postgis(
    table_name=staging_table_name,
    engine=engine,
    schema="staging",
)

# Applying transformations
config = IntegrityTransformation(**transformation_dict)
transformed = apply_transformations(data, config)

# Writing to PostGIS
write_data_to_postgis(
    data=transformed,
    table_name=final_table_name,
    engine=engine,
    schema="data",
    create_id=True,  # Add auto-increment ID column
)

# Ingesting from file
ingest_data_from_file_into_postgis(
    source_path,
    table_name,
    engine,
    schema="staging",
)

# Ingesting from URL with auth
ingest_data_from_url_into_postgis(
    url,
    table_name,
    engine,
    schema="staging",
    auth=(username, password),  # Optional tuple
)
```

### Credential Decryption

When `basic_auth_encrypted` is provided:

```python
from airflow.sdk import Variable
from data_manipulation.encryption import decrypt_credentials

encryption_key = Variable.get("datakern_encryption_key")
engine = get_datakern_sql_engine()

with engine.connect() as conn:
    username, password = decrypt_credentials(
        conn,
        basic_auth_encrypted,
        encryption_key,
    )
    auth = (username, password)
```

## Typical Workflows

### Staging DAG Workflow

1. Receive params: `source`, `source_type`, `staging_table_name`, callbacks
2. Branch based on `source_type` (`FILE` vs `URL`)
3. Ingest data to `staging.{staging_table_name}` using data_manipulation
4. Call `success_callback_url` on completion
5. Call `failure_callback_url` on error

### Process DAG Workflow

1. Receive params: either `staging_table_name` OR (`source` + `source_type`)
2. Branch: use existing staging OR re-ingest to temp staging
3. If re-ingesting: trigger ingestion task group
4. Read from staging table
5. Apply `integrity_transformation` config
6. Write to `data.{final_table_name}`
7. Call `success_callback_url` on completion

### Dynamic DAG Workflow

1. Query `datakern.integrity_link` for `schedule_enabled = true`
2. For each row, create DAG `ingestion_{id}`
3. Set schedule from `schedule` column
4. DAG triggers `process_dag` with config from row
5. Pass `source_url`, `source_type`, `final_table_name`, etc.

## Callback Integration

### Backend Expectations

Callbacks are POST requests to backend endpoints:

- **Success callback**: updates `integrity_link` with completion time, status
- **Failure callback**: logs error, potentially sets error state

### Callback URL Format

```
{backend_base_url}/api/callbacks/dags/{action}/{integrity_link_id}
```

Example: `http://backend:8000/api/callbacks/dags/success/3554b185-baf0-4d53-a8f0-e9bb358deafe`

### Callback Security

- Callbacks should only be callable from Airflow (network isolation or auth tokens)
- URLs are passed as DAG params from trusted backend
- Backend validates authenticity before processing

## Code Quality

### Type Hints

Always use type hints:

```python
def my_function(param: str, engine: Engine) -> GeoDataFrame:
    ...

def task_impl(**context: dict[str, Any]) -> None:
    ...
```

Use `X | None` not `Optional[X]`:

```python
staging_table_name: str | None = params.get("staging_table_name")
```

### Error Handling

Wrap external operations:

```python
try:
    ingest_data_from_file_into_postgis(...)
except Exception as e:
    logger.error(f"Ingestion failed: {e}")
    raise AirflowException(f"Failed to ingest: {e}")
```

### Parameter Validation

Validate required params early:

```python
params = context.get("params", {})
final_table_name = params.get("final_table_name")

if not final_table_name or not final_table_name.strip():
    raise AirflowException("final_table_name is required")
```

### Logging Best Practices

Log at appropriate levels:

```python
logger.info(f"Starting ingestion for table: {table_name}")
logger.info(f"Read {len(data)} rows from staging")
logger.error(f"Failed to connect to database: {e}")
```

Include context in logs:
- Table names, IDs, file paths
- Row counts, processing times
- Error messages with specifics

## Common Pitfalls

### XCom Task IDs

When pulling XCom from branch paths, use correct task ID:

```python
# Wrong - assumes path
value = ti.xcom_pull(task_ids="my_task")

# Right - knows it came from branch decision
staging = params.get("staging_table_name")
if not staging:
    staging = ti.xcom_pull(task_ids="generate_staging_name")
```

### Task Group References

Full path needed for branching into groups:

```python
# Wrong
return "my_task"

# Right
return f"{group_id}.my_task"
```

### Callback Failures

Don't let callback failures fail DAG:

```python
# callback.py handles this correctly:
try:
    response = requests.post(callback_url, timeout=10)
    response.raise_for_status()
except requests.RequestException as e:
    logger.error(f"Callback failed: {e}")
    # Don't raise - just log
```

### Param Type Declarations

Use proper JSON Schema types for Param():

```python
# Nullable string
Param(default=None, type=["null", "string"])

# Required string with validation
Param(default="", type="string", minLength=1)

# Enum
Param(default="FILE", type="string", enum=["FILE", "URL"])

# Object
Param(default={}, type="object")
```

## Testing Checklist

Before deploying a DAG:

- [ ] Test with valid params via Airflow UI
- [ ] Test all branch paths
- [ ] Test with missing optional params
- [ ] Verify XCom data flows correctly
- [ ] Check logs for each task
- [ ] Verify callbacks are called with correct URLs
- [ ] Test error handling (simulate failures)
- [ ] Confirm database tables created correctly
- [ ] Validate transformations applied as expected
- [ ] Check that dynamic DAGs appear when enabled
