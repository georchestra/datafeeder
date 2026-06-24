"""Tests for the transformation task group trigger-rule wiring."""

import importlib.util
import sys
import types
from pathlib import Path

import pytest


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
    dm_stub.CHUNK_SIZE = 10000  # type: ignore[attr-defined]
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


def _build_read_task(**factory_kwargs) -> _FakeTask:
    """Build the group and return its read_transform_write_task wrapper."""
    _TASK_REGISTRY.clear()
    group = _transformation.process_transformation_group(**factory_kwargs)
    group()
    return _TASK_REGISTRY["read_transform_write_task"]


class TestReadTransformWriteChunking:
    """The read/transform/write task streams the staging table in chunks."""

    class _FakeFrame:
        def __init__(self, n: int) -> None:
            self._n = n

        @property
        def empty(self) -> bool:
            return self._n == 0

        def __len__(self) -> int:
            return self._n

    def _run_task(self, monkeypatch, chunk_lengths, chunk_size=2):
        """Execute the task with read_and_transform_data yielding chunk_lengths."""
        read_calls: list[dict] = []
        write_calls: list[dict] = []

        frames = [self._FakeFrame(n) for n in chunk_lengths]

        def fake_read(**kwargs):
            read_calls.append(kwargs)
            return frames.pop(0) if frames else self._FakeFrame(0)

        def fake_write(**kwargs):
            write_calls.append(kwargs)

        monkeypatch.setattr(_transformation, "CHUNK_SIZE", chunk_size)
        monkeypatch.setattr(_transformation, "read_and_transform_data", fake_read)
        monkeypatch.setattr(_transformation, "write_data_to_postgis", fake_write)
        monkeypatch.setattr(_transformation, "create_schema", lambda *a, **kw: None)
        monkeypatch.setattr(_transformation, "get_data_sql_engine", lambda: object())
        monkeypatch.setattr(_transformation, "get_staging_schema", lambda: "staging")

        task = _build_read_task(group_id="g")
        context = {
            "params": {
                "final_table_name": "final_t",
                "staging_table_name": "staging_t",
                "integrity_transformation": {},
            },
            "ti": object(),
        }
        task.fn(**context)
        return read_calls, write_calls

    def test_streams_in_chunks_with_offsets(self, monkeypatch):
        """Two full chunks then a short chunk: reads paginate by offset, writes append."""
        read_calls, write_calls = self._run_task(monkeypatch, [2, 2, 1], chunk_size=2)

        assert [c["offset"] for c in read_calls] == [0, 2, 4]
        assert all(c["limit"] == 2 for c in read_calls)

        assert len(write_calls) == 3
        assert write_calls[0]["if_exists"] == "replace"
        assert write_calls[0]["create_id"] is True
        assert all(w["if_exists"] == "append" for w in write_calls[1:])
        assert all(w["create_id"] is False for w in write_calls[1:])

    def test_short_first_chunk_stops_after_one_read(self, monkeypatch):
        """A first chunk smaller than CHUNK_SIZE ends the loop without an extra query."""
        read_calls, write_calls = self._run_task(monkeypatch, [1], chunk_size=2)

        assert len(read_calls) == 1
        assert len(write_calls) == 1
        assert write_calls[0]["if_exists"] == "replace"

    def test_empty_staging_raises(self, monkeypatch):
        """An empty staging table raises and never writes."""
        with pytest.raises(Exception, match="Failed to transform and load data"):
            self._run_task(monkeypatch, [0], chunk_size=2)


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
