import os
from datetime import timedelta
from typing import Any, TypeVar

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import Variable
from sqlalchemy.engine import Engine

T = TypeVar("T")


def get_datafeeder_pg_hook() -> PostgresHook:
    """Create and return a PostgresHook using Airflow Connection."""
    hook = PostgresHook("DATAFEEDER_PG")
    hook.schema = "datafeeder"
    return hook


def get_data_sql_engine() -> Engine:
    """Get SQLAlchemy engine from PostgresHook."""
    return PostgresHook("DATA_PG").get_sqlalchemy_engine()


def get_source_sql_engine(db_key: str) -> Engine:
    """Get SQLAlchemy engine for a source database by its key.

    The db_key matches both the SOURCE_DATABASES backend config key
    and the Airflow connection name, enabling zero-config multi-DB support.
    """
    return PostgresHook(db_key).get_sqlalchemy_engine()


def get_datafeeder_sql_engine() -> Engine:
    """Get SQLAlchemy engine for Datafeeder from PostgresHook."""
    return get_datafeeder_pg_hook().get_sqlalchemy_engine()


def get_final_schema() -> str:
    """Get the final schema from Airflow Variable, defaulting to 'data'."""
    return Variable.get("final_schema", "data")


def get_staging_schema() -> str:
    """Get the staging schema from Airflow Variable, defaulting to 'staging'."""
    return "staging"


def get_staging_timeout() -> timedelta:
    """Get the staging task execution timeout from AIRFLOW_STAGING_TIMEOUT_SECONDS env var, defaulting to 600s."""
    try:
        seconds = int(os.environ.get("AIRFLOW_STAGING_TIMEOUT_SECONDS", "600"))
        if seconds <= 0:
            raise ValueError
    except ValueError:
        seconds = 600
    return timedelta(seconds=seconds)


def get_records_as_dicts(sql: str) -> list[dict[str, Any]]:
    """Run *sql* on the Datafeeder database and return rows as dicts.

    SQL NULLs come back as ``None``. Uses a raw cursor so the ELT image needs
    no pandas dependency.
    """
    conn = get_datafeeder_pg_hook().get_conn()
    with conn.cursor() as cursor:
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def normalize_nan(value: T | None, default: T) -> T:
    """Normalize NaN/None values to a default.

    Database NULLs read through a raw cursor come back as ``None``; this also
    guards against float ``NaN`` (which is truthy and would defeat the common
    `value or default` pattern).

    Args:
        value: The value to check (can be None, NaN, or any valid value)
        default: The value to return if value is NaN/None

    Returns:
        The original value if it's not NaN/None, otherwise the default
    """
    if value is None:
        return default
    if isinstance(value, float) and value != value:
        return default
    return value
