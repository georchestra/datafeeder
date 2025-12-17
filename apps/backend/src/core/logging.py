import logging
from functools import lru_cache


@lru_cache
def get_logger() -> logging.Logger:
    """Get a cached logger instance for the application."""

    return logging.getLogger("uvicorn.error")
