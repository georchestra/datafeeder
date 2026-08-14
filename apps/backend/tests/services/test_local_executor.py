from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.core.task_executor import TaskStatus
from src.services.executors.local_executor import LocalTaskExecutor


class _ImmediateExecutor:
    """Test double for ThreadPoolExecutor: runs submitted work synchronously."""

    def submit(self, fn, *args, **kwargs):  # type: ignore[no-untyped-def]
        fn(*args, **kwargs)


def _sync_executor() -> LocalTaskExecutor:
    executor = LocalTaskExecutor()
    executor._pool = _ImmediateExecutor()  # type: ignore[assignment]
    return executor


class TestLocalTaskExecutorStaging:
    def test_trigger_staging_task_file_success(self) -> None:
        executor = _sync_executor()

        with (
            patch(
                "src.services.executors.local_executor.ingest_data_from_file_into_postgis"
            ) as mock_ingest,
            patch("src.services.executors.local_executor.requests.post") as mock_post,
        ):
            result = executor.trigger_staging_task(
                run_id="run-1",
                staging_table_name="stg_table",
                source="/tmp/data.csv",
                source_type="FILE",
                success_callback_url="https://ok.example.com",
                failure_callback_url="https://ko.example.com",
            )

            assert result.task_id == "staging_dag"
            assert result.run_id == "run-1"
            assert result.status == TaskStatus.SUCCESS

            args, kwargs = mock_ingest.call_args
            assert args[0] == "/tmp/data.csv"
            assert args[1] == "stg_table"
            assert kwargs["schema"] == "staging"

            mock_post.assert_called_once_with("https://ok.example.com", timeout=10)

            status = executor.get_task_status("staging_dag", "run-1")
            assert status.status == TaskStatus.SUCCESS
            assert executor.get_task_logs("staging_dag", "run-1") == ""

    def test_trigger_staging_task_url_decrypts_credentials_via_datafeeder_engine(self) -> None:
        executor = _sync_executor()

        with (
            patch(
                "src.services.executors.local_executor.ingest_data_from_url_into_postgis"
            ) as mock_ingest,
            patch(
                "src.services.executors.local_executor.decrypt_basic_auth",
                return_value=("user", "pwd"),
            ) as mock_decrypt,
            patch(
                "src.services.executors.local_executor.datafeeder_engine"
            ) as mock_datafeeder_engine,
            patch("src.services.executors.local_executor.requests.post"),
        ):
            executor.trigger_staging_task(
                run_id="run-2",
                staging_table_name="stg_table",
                source="https://example.com/data.csv",
                source_type="URL",
                encrypted_credentials="enc-creds",
            )

            mock_datafeeder_engine.connect.assert_called_once()
            assert mock_decrypt.call_args.args[1] == "enc-creds"

            _, kwargs = mock_ingest.call_args
            assert kwargs["auth"] == ("user", "pwd")

    def test_trigger_staging_task_failure_calls_failure_callback_with_empty_reason(self) -> None:
        executor = _sync_executor()

        with (
            patch(
                "src.services.executors.local_executor.ingest_data_from_file_into_postgis",
                side_effect=RuntimeError("boom"),
            ),
            patch("src.services.executors.local_executor.requests.post") as mock_post,
        ):
            executor.trigger_staging_task(
                run_id="run-3",
                staging_table_name="stg_table",
                source="/tmp/missing.csv",
                source_type="FILE",
                success_callback_url="https://ok.example.com",
                failure_callback_url="https://ko.example.com",
            )

            mock_post.assert_called_once_with("https://ko.example.com&reason=", timeout=10)

            status = executor.get_task_status("staging_dag", "run-3")
            assert status.status == TaskStatus.FAILED
            assert "boom" in executor.get_task_logs("staging_dag", "run-3")

    def test_trigger_staging_task_unsupported_source_type_fails(self) -> None:
        executor = _sync_executor()

        with patch("src.services.executors.local_executor.requests.post") as mock_post:
            executor.trigger_staging_task(
                run_id="run-4",
                staging_table_name="stg_table",
                source="whatever",
                source_type="UNKNOWN",
                failure_callback_url="https://ko.example.com",
            )

            assert executor.get_task_status("staging_dag", "run-4").status == TaskStatus.FAILED
            mock_post.assert_called_once_with("https://ko.example.com&reason=", timeout=10)

    def test_get_task_status_unknown_run_raises(self) -> None:
        executor = _sync_executor()
        with pytest.raises(ValueError):
            executor.get_task_status("staging_dag", "unknown")

    def test_get_task_note_always_none(self) -> None:
        executor = _sync_executor()
        assert executor.get_task_note("staging_dag", "whatever") is None


class TestLocalTaskExecutorDatabaseSource:
    def test_trigger_staging_task_database_success(self) -> None:
        executor = _sync_executor()

        with (
            patch("src.services.executors.local_executor.source_db_key", "mydb"),
            patch(
                "src.services.executors.local_executor.source_engine", MagicMock()
            ) as mock_source_engine,
            patch(
                "src.services.executors.local_executor.ingest_data_from_database_into_postgis"
            ) as mock_ingest,
            patch("src.services.executors.local_executor.requests.post") as mock_post,
        ):
            executor.trigger_staging_task(
                run_id="run-db-1",
                staging_table_name="stg_table",
                source="db://mydb/public/mytable",
                source_type="DATABASE",
                success_callback_url="https://ok.example.com",
            )

            _, kwargs = mock_ingest.call_args
            assert kwargs["source_schema"] == "public"
            assert kwargs["source_table"] == "mytable"
            assert kwargs["target_table"] == "stg_table"
            assert kwargs["source_engine"] is mock_source_engine

            assert executor.get_task_status("staging_dag", "run-db-1").status == TaskStatus.SUCCESS
            mock_post.assert_called_once_with("https://ok.example.com", timeout=10)

    def test_trigger_staging_task_database_invalid_source_format_fails(self) -> None:
        executor = _sync_executor()

        with patch("src.services.executors.local_executor.requests.post") as mock_post:
            executor.trigger_staging_task(
                run_id="run-db-2",
                staging_table_name="stg_table",
                source="not-a-db-uri",
                source_type="DATABASE",
                failure_callback_url="https://ko.example.com",
            )

            status = executor.get_task_status("staging_dag", "run-db-2")
            assert status.status == TaskStatus.FAILED
            assert "Invalid database source URL format" in executor.get_task_logs(
                "staging_dag", "run-db-2"
            )
            mock_post.assert_called_once_with("https://ko.example.com&reason=", timeout=10)

    def test_trigger_staging_task_database_unknown_key_fails(self) -> None:
        executor = _sync_executor()

        with (
            patch("src.services.executors.local_executor.source_db_key", "otherdb"),
            patch("src.services.executors.local_executor.source_engine", MagicMock()),
            patch("src.services.executors.local_executor.requests.post") as mock_post,
        ):
            executor.trigger_staging_task(
                run_id="run-db-3",
                staging_table_name="stg_table",
                source="db://mydb/public/mytable",
                source_type="DATABASE",
                failure_callback_url="https://ko.example.com",
            )

            status = executor.get_task_status("staging_dag", "run-db-3")
            assert status.status == TaskStatus.FAILED
            assert "Unknown or unconfigured source database key" in executor.get_task_logs(
                "staging_dag", "run-db-3"
            )
            mock_post.assert_called_once_with("https://ko.example.com&reason=", timeout=10)


class TestLocalTaskExecutorProcess:
    def test_trigger_process_task_success(self) -> None:
        executor = _sync_executor()
        chunk = pd.DataFrame({"a": [1, 2]})

        with (
            patch("src.services.executors.local_executor.create_schema") as mock_create_schema,
            patch(
                "src.services.executors.local_executor.read_and_transform_data",
                return_value=chunk,
            ) as mock_read,
            patch("src.services.executors.local_executor.write_data_to_postgis") as mock_write,
            patch("src.services.executors.local_executor.Table") as mock_table_cls,
            patch("src.services.executors.local_executor.data_engine"),
            patch("src.services.executors.local_executor.requests.post") as mock_post,
        ):
            executor.trigger_process_task(
                run_id="run-p1",
                staging_table_name="stg_table",
                final_table_name="final_table",
                integrity_transformation={},
                success_callback_url="https://ok.example.com",
                failure_callback_url="https://ko.example.com",
                target_schema="data",
            )

            mock_create_schema.assert_called_once()
            assert mock_read.call_args.kwargs["table_name"] == "stg_table"
            assert mock_read.call_args.kwargs["offset"] == 0

            assert mock_write.call_args.kwargs["create_id"] is True
            assert mock_write.call_args.kwargs["if_exists"] == "replace"

            # staging table dropped after a successful transform
            mock_table_cls.assert_called_once()
            mock_table_cls.return_value.drop.assert_called_once()

            mock_post.assert_called_once_with("https://ok.example.com", timeout=10)
            assert executor.get_task_status("process_dag", "run-p1").status == TaskStatus.SUCCESS

    def test_trigger_process_task_no_rows_fails(self) -> None:
        executor = _sync_executor()

        with (
            patch("src.services.executors.local_executor.create_schema"),
            patch(
                "src.services.executors.local_executor.read_and_transform_data",
                return_value=pd.DataFrame(),
            ),
            patch("src.services.executors.local_executor.write_data_to_postgis") as mock_write,
            patch("src.services.executors.local_executor.data_engine"),
            patch("src.services.executors.local_executor.requests.post") as mock_post,
        ):
            executor.trigger_process_task(
                run_id="run-p2",
                staging_table_name="stg_table",
                final_table_name="final_table",
                failure_callback_url="https://ko.example.com",
            )

            mock_write.assert_not_called()
            mock_post.assert_called_once_with("https://ko.example.com&reason=", timeout=10)
            status = executor.get_task_status("process_dag", "run-p2")
            assert status.status == TaskStatus.FAILED
            assert "No data to write after transformation." in executor.get_task_logs(
                "process_dag", "run-p2"
            )

    def test_trigger_process_task_missing_staging_table_name_fails(self) -> None:
        executor = _sync_executor()

        with patch("src.services.executors.local_executor.requests.post") as mock_post:
            executor.trigger_process_task(
                run_id="run-p3",
                staging_table_name=None,
                final_table_name="final_table",
                failure_callback_url="https://ko.example.com",
            )

            mock_post.assert_called_once_with("https://ko.example.com&reason=", timeout=10)
            assert executor.get_task_status("process_dag", "run-p3").status == TaskStatus.FAILED
