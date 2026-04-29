"""Logging configuration for the data_manipulation library."""

import logging


def configure_logging(parent_logger: logging.Logger) -> None:
    """Configure data_manipulation library logging to use a parent logger's handlers.

    This function connects the data_manipulation logger to a parent logger's handlers,
    ensuring that all logs from this library are properly captured by the parent
    application's logging system (e.g., uvicorn, airflow).

    If the parent logger has no handlers (e.g. called at module-load time before
    the runtime has finished configuring logging), propagation is left enabled so
    that log records can still reach the root logger instead of being silently
    dropped.

    Args:
        parent_logger: The parent logger whose handlers should be used
                       (e.g., uvicorn.error, airflow.task)

    Example:
        >>> # In a FastAPI application with uvicorn
        >>> import logging
        >>> from data_manipulation.logging import configure_logging
        >>> uvicorn_logger = logging.getLogger("uvicorn.error")
        >>> configure_logging(uvicorn_logger)

        >>> # In an Airflow DAG task function (called at runtime, not module level)
        >>> task_logger = logging.getLogger("airflow.task")
        >>> configure_logging(task_logger)
    """
    # Get the root package logger using __package__ (e.g., "data_manipulation")
    # This will configure all submodule loggers (data_manipulation.ingestion, etc.)
    data_manipulation_logger = logging.getLogger(__package__)

    # Use the parent's effective level when its own level is NOTSET (0)
    level = (
        parent_logger.level
        if parent_logger.level != logging.NOTSET
        else parent_logger.getEffectiveLevel()
    )
    data_manipulation_logger.setLevel(level if level != logging.NOTSET else logging.INFO)

    # Add parent's handlers to data_manipulation logger
    for handler in parent_logger.handlers:
        if handler not in data_manipulation_logger.handlers:
            data_manipulation_logger.addHandler(handler)

    # Only disable propagation when we actually copied handlers;
    # otherwise keep it enabled so logs reach the root logger.
    if data_manipulation_logger.handlers:
        data_manipulation_logger.propagate = False
    else:
        data_manipulation_logger.propagate = True
