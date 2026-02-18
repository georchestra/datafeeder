# Airflow Pattern Guide

Reference guide pointing to actual codebase implementations. Always check the source files for the current implementation.

## Where to Find Patterns

### Basic DAG Structure

**See:** [apps/elt/dags/staging_dag.py](../../../apps/elt/dags/staging_dag.py)

Key elements to note:
- `@dag` decorator with all required params
- Typed `Param()` definitions with validation
- `_dag_success_callback` and `_dag_failure_callback` functions
- Logger configuration: `logger = logging.getLogger(__name__)` + `configure_logging(logger)`
- DAG instance creation: `staging_dag_instance = staging_dag()`

### Advanced DAG with Branching and XCom

**See:** [apps/elt/dags/process_dag.py](../../../apps/elt/dags/process_dag.py)

Key patterns demonstrated:
- `@task.branch` for conditional workflow paths (`decide_ingestion_mode`)
- XCom communication between tasks (`generate_staging_table_name` → consumers)
- Multiple execution modes based on input params
- Integration with task groups
- Proper error handling with `AirflowException`

### Task Group Factory Pattern

**See:** [apps/elt/dags/task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py)

The `ingestion_group(group_id)` function demonstrates:
- Factory function accepting `Literal` type for group_id
- Returns `@task_group` decorated implementation
- Internal branching with `@task.branch` (`select_ingestion_mode`)
- Multiple task paths (file vs URL ingestion)
- Accessing params and XCom within task group
- Integration with data_manipulation library

**See also:** [apps/elt/dags/task_groups/transformation.py](../../../apps/elt/dags/task_groups/transformation.py)

The `process_transformation_group()` function shows:
- Optional XCom source configuration via `task_id_where_to_get_staging_table_name`
- Full read-transform-write workflow
- Using `IntegrityTransformation` from data_manipulation
- Database operations with SQLAlchemy engines

### XCom Communication

**Real examples in codebase:**

1. **Producer:** `generate_staging_table_name()` in [process_dag.py](../../../apps/elt/dags/process_dag.py)
   - Returns string value, auto-pushed to XCom

2. **Consumer:** `file_ingest_step()` and `url_ingest_step()` in [task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py)
   - Pulls value: `ti.xcom_pull(task_ids="generate_staging_table_name")`
   - Fallback to params: `params.get("staging_table_name")`

### Branching Logic

**See:** [apps/elt/dags/process_dag.py](../../../apps/elt/dags/process_dag.py) - `decide_ingestion_mode()`

Pattern:
- Use `@task.branch` decorator with `# type: ignore[misc]`
- Return task ID as string
- Raise `AirflowException` for invalid paths
- Task IDs reference can include task group: `"use_staging_table_from_context"` or `"generate_staging_table_name"`

**See also:** [apps/elt/dags/task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py) - `do_branching()`

Pattern:
- Branch within task group
- Return full task path: `f"{group_id}.file_ingest_step"` or `f"{group_id}.url_ingest_step"`
- Use match/case for clean branching logic

### Dynamic DAG Generation

**See:** [apps/elt/dags/process-dag-generator.py](../../../apps/elt/dags/process-dag-generator.py)

Key components:
- `load_scheduled_integrity_links()` - Query database for configurations
- `create_dag(config)` - Factory function creating DAG from config
- Module-level loop: `for config in load_scheduled_integrity_links(): ...`
- DAG registration: `globals()[dag_id] = create_dag(config)`
- Using `TriggerDagRunOperator` to trigger other DAGs with conf

### Database Utilities

**See:** [apps/elt/dags/utils.py](../../../apps/elt/dags/utils.py)

Functions to replicate:
- `get_datakern_pg_hook()` - PostgresHook with schema set
- `get_data_sql_engine()` - SQLAlchemy engine from hook
- `get_final_schema()` - Variable getter with default
- `get_staging_schema()` - Hardcoded schema name

Pattern: Create similar functions for your database connections.

### Callbacks

**See:** [apps/elt/dags/callback.py](../../../apps/elt/dags/callback.py)

The `call_callback()` function shows:
- HTTP POST with timeout
- Comprehensive logging (request + response)
- Error handling that logs but doesn't raise
- Response text truncation for logs

**Usage in DAGs:** See callback functions in [staging_dag.py](../../../apps/elt/dags/staging_dag.py):
- Extract URL from `context.get("params", {})`
- Call `call_callback(url, "success")` or `call_callback(url, "failure")`

### Data Manipulation Integration

**See task implementations in:**
- [task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py) - `file_ingest_step()` and `url_ingest_step()`
- [task_groups/transformation.py](../../../apps/elt/dags/task_groups/transformation.py) - `read_transform_write_task()`

Common imports and usage:
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

### Type Definitions

**See:** [apps/elt/dags/models.py](../../../apps/elt/dags/models.py)

Simple Pydantic Literal types for validation:
```python
SourceType = Literal["FILE", "URL"]
```

Create similar types as needed for your domain.

## Common Workflows

### New Basic DAG

1. Copy structure from [staging_dag.py](../../../apps/elt/dags/staging_dag.py)
2. Update dag_id, params, and callbacks
3. Implement tasks with `@task` decorator
4. Create DAG instance at module level

### New Task Group

1. Copy factory pattern from [task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py)
2. Update function signature with appropriate `Literal` types
3. Implement `@task_group` decorated inner function
4. Define tasks inside task group
5. Set up task dependencies

### Add Branching

1. Reference `decide_ingestion_mode()` in [process_dag.py](../../../apps/elt/dags/process_dag.py)
2. Use `@task.branch` with `# type: ignore[misc]`
3. Return task ID strings
4. Create all branch targets before setting up dependencies

### Use XCom

1. Producer: Return value from task (auto-pushed)
2. Consumer: Get `ti = context.get("ti")` then `ti.xcom_pull(task_ids="...")`
3. See real example in [task_groups/ingestion.py](../../../apps/elt/dags/task_groups/ingestion.py)

### Dynamic DAGs

1. Study [process-dag-generator.py](../../../apps/elt/dags/process-dag-generator.py) completely
2. Create query function for your config table
3. Create DAG factory function
4. Generate DAGs in module-level loop

