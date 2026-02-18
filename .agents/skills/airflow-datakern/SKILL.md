---
name: airflow-datakern
description: Build Apache Airflow 3.x DAGs following DataKern project patterns. Use when creating DAGs with TaskAPI decorators (@dag, @task, @task_group), implementing task groups as factory functions, setting up success/failure callbacks to external APIs, dynamic DAG generation from database, branching workflows, XCom communication, PostgreSQL integration with hooks, or working with apps/elt/dags codebase. Follows Python 3.12, ruff formatting (100 char lines), data_manipulation library integration.
---

# Airflow DataKern

Build Airflow 3.x workflows following DataKern project conventions with TaskAPI decorators, factory-based task groups, callbacks, and PostgreSQL integration.

## Core Patterns

### DAG Structure
Use `@dag` decorator with typed `Param()` objects. Include `on_success_callback` and `on_failure_callback`. Set `schedule=None` for manual triggers, `catchup=False` to prevent backfilling.

**Reference:** [apps/elt/dags/staging_dag.py](apps/elt/dags/staging_dag.py) and [apps/elt/dags/process_dag.py](apps/elt/dags/process_dag.py) for complete examples.

### Task Groups as Factory Functions
**Critical pattern:** Task groups are factory functions that return `@task_group` decorated implementations. This allows parameterized, reusable task groups.

**Reference:** 
- [apps/elt/dags/task_groups/ingestion.py](apps/elt/dags/task_groups/ingestion.py) - `ingestion_group(group_id)` factory
- [apps/elt/dags/task_groups/transformation.py](apps/elt/dags/task_groups/transformation.py) - `process_transformation_group()` factory

### Database Access
Database utilities live in [apps/elt/dags/utils.py](apps/elt/dags/utils.py):
- `get_datakern_pg_hook()` / `get_data_pg_hook()` - PostgresHook instances
- `get_datakern_sql_engine()` / `get_data_sql_engine()` - SQLAlchemy engines
- `get_final_schema()` / `get_staging_schema()` - Schema name getters

### Callbacks
Callback utilities in [apps/elt/dags/callback.py](apps/elt/dags/callback.py):
- `call_callback(url, type)` - POST to callback URL with error handling
- Implement `_dag_success_callback` and `_dag_failure_callback` in each DAG

### Error Handling
- Raise `AirflowException` for task failures
- Wrap external operations in try-except
- Log before raising: `logger.error(f"Failed: {e}")`
- Callbacks handle failures gracefully (log, don't fail DAG)

## Essential Constraints

**MUST DO:**
- Use `@dag`, `@task`, `@task_group` decorators only (no classes)
- Type hint context: `**context: dict[str, Any]`
- Define DAG params with `Param(type="string", default=..., description=...)`
- Configure logging: `logger = logging.getLogger(__name__)` + `configure_logging(logger)` from data_manipulation
- Access params: `params = context.get("params", {})`
- Pull XCom: `ti = context.get("ti")` then `ti.xcom_pull(task_ids="...")`
- Use factory functions for parameterized task groups
- Use `X | None` instead of `Optional[X]`

**MUST NOT:**
- No class-based DAGs, no `DummyOperator`
- No hardcoded credentials (use Variables/Connections)
- No skipping type hints
- No global state or mutable defaults

## Codebase Reference

All patterns are demonstrated in the actual codebase:

**Core DAGs:**
- [apps/elt/dags/staging_dag.py](apps/elt/dags/staging_dag.py) - Initial ingestion to staging tables
- [apps/elt/dags/process_dag.py](apps/elt/dags/process_dag.py) - Branching, XCom, transformation workflow
- [apps/elt/dags/process-dag-generator.py](apps/elt/dags/process-dag-generator.py) - Dynamic DAG generation from DB

**Reusable Components:**
- [apps/elt/dags/task_groups/ingestion.py](apps/elt/dags/task_groups/ingestion.py) - File/URL ingestion task group factory
- [apps/elt/dags/task_groups/transformation.py](apps/elt/dags/task_groups/transformation.py) - Transformation task group factory
- [apps/elt/dags/callback.py](apps/elt/dags/callback.py) - HTTP callback utilities
- [apps/elt/dags/utils.py](apps/elt/dags/utils.py) - Database hooks and engines
- [apps/elt/dags/models.py](apps/elt/dags/models.py) - Type definitions

**Key Patterns in Code:**
- **Factory pattern:** See `ingestion_group()` in [task_groups/ingestion.py](apps/elt/dags/task_groups/ingestion.py)
- **Branching:** See `decide_ingestion_mode()` in [process_dag.py](apps/elt/dags/process_dag.py)
- **XCom:** See how `generate_staging_table_name()` output is consumed in [task_groups/ingestion.py](apps/elt/dags/task_groups/ingestion.py)
- **Callbacks:** See `_dag_success_callback()` in [staging_dag.py](apps/elt/dags/staging_dag.py)

**Project conventions:** See [references/conventions.md](references/conventions.md) for naming, structure, and integration patterns.

## Quick Reference

**Access params:**
```python
params = context.get("params", {})
value = params.get("param_name")
```

**Pull XCom:**
```python
ti = context.get("ti")
value = ti.xcom_pull(task_ids="task_id")
```

**Branching:**
```python
@task.branch(task_id="decide")  # type: ignore[misc]
def decide(**context: dict[str, Any]) -> str:
    return "task_a" if condition else "task_b"
```

**Logging:**
```python
import logging
from data_manipulation.logging import configure_logging

logger = logging.getLogger(__name__)
configure_logging(logger)

logger.info(f"Processing: {value}")
logger.error(f"Failed: {e}")
```
```
