"""Tests for the transformation task group trigger-rule wiring."""

import importlib.util
import sys
import types
from pathlib import Path


class _FakeTask:
    """Stand-in for a decorated Airflow task: records kwargs, supports >>."""

    def __init__(self, fn, kwargs):
        self.fn = fn
        self.kwargs = kwargs

    def __call__(self, *args, **kwargs):
        return self

    def __rshift__(self, other):
        return other


_TASK_REGISTRY: dict[str, _FakeTask] = {}


def _load_transformation_module():
    """Load task_groups/transformation.py with stubbed Airflow imports."""

    def task(**task_kwargs):
        def decorator(fn):
            fake = _FakeTask(fn, task_kwargs)
            _TASK_REGISTRY[task_kwargs.get("task_id", fn.__name__)] = fake
            return fake

        return decorator

    def task_group(**_group_kwargs):
        def decorator(fn):
            return fn

        return decorator

    sdk_stub = types.ModuleType("airflow.sdk")
    sdk_stub.task = task  # type: ignore[attr-defined]
    sdk_stub.task_group = task_group  # type: ignore[attr-defined]

    exceptions_stub = types.ModuleType("airflow.exceptions")
    exceptions_stub.AirflowException = type("AirflowException", (Exception,), {})  # type: ignore[attr-defined]

    class _TriggerRule:
        ALL_SUCCESS = "all_success"
        ALL_DONE = "all_done"
        NONE_FAILED_MIN_ONE_SUCCESS = "none_failed_min_one_success"

    trigger_rule_stub = types.ModuleType("airflow.utils.trigger_rule")
    trigger_rule_stub.TriggerRule = _TriggerRule  # type: ignore[attr-defined]

    dm_stub = types.ModuleType("data_manipulation")
    dm_stub.IntegrityTransformation = type("IntegrityTransformation", (), {})  # type: ignore[attr-defined]
    dm_stub.read_and_transform_data = lambda *a, **kw: None  # type: ignore[attr-defined]
    dm_stub.write_data_to_postgis = lambda *a, **kw: None  # type: ignore[attr-defined]

    dm_db_stub = types.ModuleType("data_manipulation.database")
    dm_db_stub.create_schema = lambda *a, **kw: None  # type: ignore[attr-defined]

    sqlalchemy_stub = types.ModuleType("sqlalchemy")
    sqlalchemy_stub.MetaData = type("MetaData", (), {"__init__": lambda self, *a, **kw: None})  # type: ignore[attr-defined]
    sqlalchemy_stub.Table = type("Table", (), {"__init__": lambda self, *a, **kw: None})  # type: ignore[attr-defined]

    utils_stub = types.ModuleType("utils")
    utils_stub.get_data_sql_engine = lambda: None  # type: ignore[attr-defined]
    utils_stub.get_staging_schema = lambda: "staging"  # type: ignore[attr-defined]

    stubs = {
        "airflow": types.ModuleType("airflow"),
        "airflow.sdk": sdk_stub,
        "airflow.exceptions": exceptions_stub,
        "airflow.utils": types.ModuleType("airflow.utils"),
        "airflow.utils.trigger_rule": trigger_rule_stub,
        "data_manipulation": dm_stub,
        "data_manipulation.database": dm_db_stub,
        "sqlalchemy": sqlalchemy_stub,
        "utils": utils_stub,
    }

    # Override sys.modules during the import only, then restore — other test
    # modules (e.g. test_process_dag_generator) install their own stubs under
    # the same names.
    saved = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        source = Path(__file__).parent.parent / "task_groups" / "transformation.py"
        spec = importlib.util.spec_from_file_location("transformation_under_test", source)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, prev in saved.items():
            if prev is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = prev
    return module


_transformation = _load_transformation_module()


def _clean_task_kwargs(**factory_kwargs) -> dict:
    """Build the group and return the kwargs of its clean_staging_table_task."""
    _TASK_REGISTRY.clear()
    group = _transformation.process_transformation_group(**factory_kwargs)
    group()  # execute the group body so the @task decorators run
    return _TASK_REGISTRY["clean_staging_table_task"].kwargs


class TestCleanStagingTableTriggerRule:
    def test_default_keeps_all_success(self):
        """Direct mode: the tracked staging table must survive a transform failure."""
        kwargs = _clean_task_kwargs(
            group_id="transform_direct",
            task_id_where_to_get_staging_table_name="use_staging_table_from_context",
        )
        assert kwargs["trigger_rule"] == "all_success"

    def test_clean_on_failure_uses_all_done(self):
        """Refresh mode: the temp staging table must be dropped even on failure."""
        kwargs = _clean_task_kwargs(
            group_id="transform_refresh",
            task_id_where_to_get_staging_table_name="generate_staging_table_name",
            clean_on_failure=True,
        )
        assert kwargs["trigger_rule"] == "all_done"

    def test_read_task_trigger_rule_unchanged(self):
        """The read/transform/write task keeps its branch-aware trigger rule."""
        _clean_task_kwargs(group_id="g", clean_on_failure=True)
        read_kwargs = _TASK_REGISTRY["read_transform_write_task"].kwargs
        assert read_kwargs["trigger_rule"] == "none_failed_min_one_success"
