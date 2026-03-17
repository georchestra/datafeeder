"""Factory for creating task executors based on configuration."""

from functools import lru_cache

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.task_executor import BaseTaskExecutor, TaskExecutorType
from src.services.executors.airflow_executor import AirflowTaskExecutor

logger = get_logger()


@lru_cache
def get_task_executor() -> BaseTaskExecutor:
    """
    Get the configured task executor.

    Returns:
        BaseTaskExecutor: Configured task executor instance (Airflow)
    """
    settings = get_settings()
    executor_type = settings.TASK_EXECUTOR

    logger.info(f"Using task executor: {executor_type}")

    if executor_type == TaskExecutorType.AIRFLOW:
        return AirflowTaskExecutor()

    else:
        raise ValueError(f"Unknown task executor type: {executor_type}")


__all__ = ["get_task_executor"]
