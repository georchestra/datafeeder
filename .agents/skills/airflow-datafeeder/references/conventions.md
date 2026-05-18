# Datafeeder Project Conventions

Project-specific naming, organization, and integration rules. Always reference actual codebase for current implementation.

## File Organization

See [apps/elt/dags/](../../../apps/elt/dags/) structure:

```
apps/elt/dags/
├── callback.py               # HTTP callback utilities
├── models.py                 # Type definitions (SourceType, etc.)
├── utils.py                  # Database hooks, engines, schema getters
├── staging_dag.py            # Initial ingestion to staging schema
├── process_dag.py            # Transform staging → final table
├── process-dag-generator.py  # Dynamic DAGs from integrity_link
└── task_groups/
    ├── ingestion.py          # Reusable ingestion task group factory
    └── transformation.py     # Reusable transformation task group factory
```

## Naming Conventions

### Files and DAGs
- **DAG files**: `{purpose}_dag.py` → `staging_dag.py`, `process_dag.py`
- **DAG IDs**: `{purpose}_dag` → `staging_dag`, `process_dag`
- **Dynamic DAG IDs**: `ingestion_{integrity_link_id}` (see [process-dag-generator.py](../../../apps/elt/dags/process-dag-generator.py))
- **Generator files**: `{purpose}-dag-generator.py`

### Tasks and Groups
- **Task IDs**: `{action}_step` → `file_ingest_step`, `url_ingest_step`
- **Alternative**: `{purpose}_task` → `read_transform_write_task`
- **Task group IDs**: `{purpose}_{mode}` → `initial_ingestion`, `refresh_ingestion`
- **Branch task IDs**: `decide_{purpose}` → `decide_ingestion_mode`

### Functions
- **Callbacks**: `_dag_{success|failure}_callback` (leading underscore, see any DAG file)
- **Utilities**: `get_{resource}_hook()`, `get_{resource}_engine()` (see [utils.py](../../../apps/elt/dags/utils.py))
- **Factory functions**: `{name}_group(group_id: Literal[...])` returns `@task_group` (see task_groups/)
- **Internal implementations**: `_impl()` or `_{name}_impl()` (inside factory functions)

### Standard Parameters

**Check actual DAG params in [staging_dag.py](../../../apps/elt/dags/staging_dag.py) and [process_dag.py](../../../apps/elt/dags/process_dag.py)**

Common parameter names:
- Tables: `staging_table_name`, `final_table_name`
- Source: `source`, `source_url`, `source_type`, `source_import_type`
- Auth: `basic_auth_encrypted`, `source_auth_enabled`, `source_password_encrypted`
- Callbacks: `success_callback_url`, `failure_callback_url`
- Config: `integrity_transformation`, `config_json`
- Schedule: `schedule`, `schedule_enabled`

## Datafeeder Database Integration

### Main Table: `datafeeder.integrity_link`

Query example in [process-dag-generator.py](../../../apps/elt/dags/process-dag-generator.py):

Key columns:
- `id`, `data_id`, `metadata_id`
- `integrity_title`, `staging_table_name`, `final_table_name`
- `schedule`, `schedule_enabled`
- `integrity_transformation` (JSONB config)
- `source_url`, `source_import_type`, `source_password_encrypted`
- `staging_retrieve_time`, `last_retrieval_timestamp`
- `integrity_owner`, `integrity_organization`

### Schema Organization

Defined in [utils.py](../../../apps/elt/dags/utils.py):
- **Staging schema**: `"staging"` via `get_staging_schema()`
- **Final schema**: `Variable.get("final_schema", "data")` via `get_final_schema()`

## Data Manipulation Library Integration

### Required Imports

See usage in [task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py) and [task_groups/transformation.py](../../../apps/elt/dags/task_groups/transformation.py):

```python
from data_manipulation.logging import configure_logging
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

### Logger Configuration

**Every DAG/task group file must have:**
```python
import logging
from data_manipulation.logging import configure_logging

logger = logging.getLogger(__name__)
configure_logging(logger)
```

See any DAG file for this pattern.

### Credential Decryption

**See:** [task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py) in `url_ingest_step()`:

Pattern:
1. Get encrypted value from params: `basic_auth_encrypted`
2. Get encryption key from Variables: `Variable.get("datafeeder_encryption_key")`
3. Get datafeeder engine
4. Call `decrypt_credentials(conn, encrypted, key)` → returns `(username, password)`
5. Pass as tuple to ingestion: `auth=(username, password)`

## Typical Workflows

Study actual DAGs for complete workflows:

### Staging DAG
See [apps/elt/dags/staging_dag.py](../../../apps/elt/dags/staging_dag.py):
1. Receive params (source, source_type, staging_table_name, callbacks)
2. Delegate to `ingestion_group("initial_ingestion")`
3. Call success/failure callback on completion

### Process DAG
See [apps/elt/dags/process_dag.py](../../../apps/elt/dags/process_dag.py):
1. Branch: use existing staging OR re-ingest to temp staging
2. If re-ingesting: delegate to `ingestion_group("refresh_ingestion")`
3. Delegate to `process_transformation_group()` for transformation
4. Call success/failure callback on completion

### Dynamic Generation
See [apps/elt/dags/process-dag-generator.py](../../../apps/elt/dags/process-dag-generator.py):
1. Query `datafeeder.integrity_link WHERE schedule_enabled = true`
2. For each row: `create_dag(config)` with `dag_id = f"ingestion_{config['id']}"`
3. Register in globals: `globals()[dag_id] = create_dag(config)`
4. Each dynamic DAG triggers `process_dag` with configuration

## Code Quality Requirements

### Type Hints
**Always required.** See [ruff.toml](../../../ruff.toml) and project files:
- Use `dict[str, Any]` for context
- Use `X | None` not `Optional[X]`
- Type hint function returns

### Error Handling
**See implementations in task_groups:**
- `raise AirflowException(f"message: {e}")` for task failures
- Wrap external operations in try-except
- Log before raising: `logger.error(f"Failed: {e}")`
- Callbacks log but don't raise (see [callback.py](../../../apps/elt/dags/callback.py))

### Parameter Validation
**See process_dag.py and task_groups:**
- Check required params early: `if not value: raise AirflowException(...)`
- Handle optional params: `value = params.get("key")` then `if value:`
- Validate before use, not during use

### Logging
**See any DAG/task group file:**
- Info level: workflow progress, table names, row counts
- Error level: failures with context
- Include specifics: `logger.info(f"Read {len(data)} rows from {table_name}")`

## Formatting Rules

From [ruff.toml](../../../ruff.toml):
- **Line length**: 100 characters
- **Import sorting**: Enabled (ruff extend-select = ["I"])
- **Python version**: 3.12 (see [pyproject.toml](../../../apps/elt/pyproject.toml))

## Common Mistakes

### XCom Task IDs
Wrong: Assume task ID without checking
Right: Try params first, fallback to XCom with correct task_id
See: [task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py) `file_ingest_step()`

### Task Group References in Branching
Wrong: Return `"my_task"` from branch
Right: Return `f"{group_id}.my_task"`
See: [task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py) `do_branching()`

### Callback Failures
Wrong: Let callback exceptions fail DAG
Right: Log error but don't raise
See: [callback.py](../../../apps/elt/dags/callback.py)

### Param Type Declarations
Check [staging_dag.py](../../../apps/elt/dags/staging_dag.py) params for correct Param() usage:
- Nullable: `type=["null", "string"]`
- Required with validation: `type="string", minLength=1`
- Enum: `type="string", enum=["FILE", "URL"]`
- Object: `type="object"`

## Testing Approach

Before deploying:
- Test via Airflow UI with valid params
- Test all branch paths
- Verify XCom flows
- Check logs for each task
- Confirm callbacks work
- Simulate failures for error handling
- Validate database operations
