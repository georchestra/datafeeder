"""Task executor abstraction layer for Airflow and others."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from src.core.constants import DEFAULT_DATA_SCHEMA


class TaskExecutorType(str, Enum):
    """Type of task executor to use."""

    AIRFLOW = "AIRFLOW"
    # CELERY = "CELERY"


class TaskStatus(str, Enum):
    """Unified task status across executors."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    UP_FOR_RETRY = "up_for_retry"
    UP_FOR_RESCHEDULE = "up_for_reschedule"
    UPSTREAM_FAILED = "upstream_failed"
    SKIPPED = "skipped"
    DEFERRED = "deferred"
    REMOVED = "removed"
    RESTARTING = "restarting"


class TaskRunInfo(BaseModel):
    """Unified task run information."""

    task_id: str
    run_id: str
    status: TaskStatus
    execution_date: str | None = None


class BaseTaskExecutor(ABC):
    """Base class for task executors."""

    @abstractmethod
    def trigger_staging_task(
        self,
        run_id: str,
        staging_table_name: str,
        source: str,
        source_type: str,
        success_callback_url: str | None = None,
        failure_callback_url: str | None = None,
        encrypted_credentials: str | None = None,
        source_layer: str | None = None,
        source_protocol: str | None = None,
        generate_metadata_with_ai: bool = False,
    ) -> TaskRunInfo:
        """
        Trigger a staging task.

        Args:
            run_id: Unique identifier for this run
            staging_table_name: Name of the staging table
            source: Source path or URL
            source_type: Type of source (FILE, URL, etc.)
            success_callback_url: URL to call on success
            failure_callback_url: URL to call on failure
            encrypted_credentials: Encrypted credentials if needed

        Returns:
            TaskRunInfo with task details
        """
        pass

    @abstractmethod
    def trigger_process_task(
        self,
        run_id: str,
        staging_table_name: str | None = None,
        final_table_name: str = "",
        integrity_transformation: dict[str, Any] | None = None,
        success_callback_url: str | None = None,
        failure_callback_url: str | None = None,
        last_retrieval_timestamp: datetime | None = None,
        target_schema: str = DEFAULT_DATA_SCHEMA,
        generate_metadata_with_ai: bool = False,
    ) -> TaskRunInfo:
        """
        Trigger a process task.

        Args:
            run_id: Unique identifier for this run
            staging_table_name: Name of existing staging table
            final_table_name: Name of the final table to create
            integrity_transformation: JSON configuration for transformations
            success_callback_url: URL to call on success
            failure_callback_url: URL to call on failure
            target_schema: PostgreSQL schema for the final table

        Returns:
            TaskRunInfo with task details
        """
        pass

    @abstractmethod
    def get_task_status(self, task_id: str, run_id: str) -> TaskRunInfo:
        """
        Get the status of a task.

        Args:
            task_id: Task identifier
            run_id: Run identifier

        Returns:
            TaskRunInfo with current task status
        """
        pass

    @abstractmethod
    def get_task_logs(self, task_id: str, run_id: str) -> str:
        """
        Get logs for a task.

        Args:
            task_id: Task identifier
            run_id: Run identifier

        Returns:
            Task logs as string
        """
        pass

    @abstractmethod
    def get_task_note(self, task_id: str, run_id: str) -> str | None:
        """
        Get the note attached to a task run.

        Args:
            task_id: Task identifier
            run_id: Run identifier

        Returns:
            Note string if present, None otherwise
        """
        pass
