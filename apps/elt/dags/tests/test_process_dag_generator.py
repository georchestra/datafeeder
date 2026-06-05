"""Tests for process-dag-generator callback URL construction."""

import importlib.util
import sys
import types
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def _load_build_callback_url():
    """Load _build_callback_url from process-dag-generator.py without executing Airflow code."""
    # Build minimal stubs so the module-level Airflow imports don't fail
    airflow_stub = types.ModuleType("airflow")
    airflow_stub.DAG = type("DAG", (), {"__init__": lambda self, *a, **kw: None})  # type: ignore[attr-defined]

    trigger_stub = types.ModuleType("airflow.providers.standard.operators.trigger_dagrun")
    trigger_stub.TriggerDagRunOperator = type(  # type: ignore[attr-defined]
        "TriggerDagRunOperator", (), {"__init__": lambda self, *a, **kw: None}
    )

    for mod_name, stub in [
        ("airflow", airflow_stub),
        ("airflow.providers", types.ModuleType("airflow.providers")),
        ("airflow.providers.standard", types.ModuleType("airflow.providers.standard")),
        (
            "airflow.providers.standard.operators",
            types.ModuleType("airflow.providers.standard.operators"),
        ),
        ("airflow.providers.standard.operators.trigger_dagrun", trigger_stub),
    ]:
        sys.modules.setdefault(mod_name, stub)

    class _FakeDF:
        def to_dict(self, orient):
            return []

    class _FakeHook:
        def get_pandas_df(self, sql):
            return _FakeDF()

    utils_stub = types.ModuleType("utils")
    utils_stub.get_datafeeder_pg_hook = lambda: _FakeHook()  # type: ignore[attr-defined]
    utils_stub.normalize_nan = lambda value, default: default if value is None else value  # type: ignore[attr-defined]
    sys.modules["utils"] = utils_stub

    source = Path(__file__).parent.parent / "process-dag-generator.py"
    spec = importlib.util.spec_from_file_location("process_dag_generator", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module._build_callback_url  # type: ignore[attr-defined]


_build_callback_url = _load_build_callback_url()


class TestBuildCallbackUrl:
    def test_success_url_uses_backend_url_env(self, monkeypatch):
        monkeypatch.setenv("BACKEND_INTERNAL_URL", "http://my-backend:9000")
        url = _build_callback_url("/ingestion/process/dag_success", "abc-123", "my_table")
        parsed = urlparse(url)
        assert parsed.scheme == "http"
        assert parsed.netloc == "my-backend:9000"
        assert parsed.path == "/ingestion/process/dag_success"

    def test_success_url_contains_integrity_link_id(self, monkeypatch):
        monkeypatch.setenv("BACKEND_INTERNAL_URL", "http://datafeeder-backend:8000")
        url = _build_callback_url("/ingestion/process/dag_success", "abc-123", "my_table")
        qs = parse_qs(urlparse(url).query)
        assert qs["integrity_link_id"] == ["abc-123"]

    def test_success_url_contains_final_table_name(self, monkeypatch):
        monkeypatch.setenv("BACKEND_INTERNAL_URL", "http://datafeeder-backend:8000")
        url = _build_callback_url("/ingestion/process/dag_success", "abc-123", "my_table")
        qs = parse_qs(urlparse(url).query)
        assert qs["final_table_name"] == ["my_table"]

    def test_failure_url_points_to_dag_failure_endpoint(self, monkeypatch):
        monkeypatch.setenv("BACKEND_INTERNAL_URL", "http://datafeeder-backend:8000")
        url = _build_callback_url("/ingestion/process/dag_failure", "abc-123", "my_table")
        assert urlparse(url).path == "/ingestion/process/dag_failure"

    def test_default_backend_url_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("BACKEND_INTERNAL_URL", raising=False)
        url = _build_callback_url("/ingestion/process/dag_success", "abc-123", "my_table")
        assert url.startswith("http://datafeeder-backend:8000")
