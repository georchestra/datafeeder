import os
from datetime import timedelta

from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import Variable
from sqlalchemy.engine import Engine


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
    """Get the staging task execution timeout from STAGING_TIMEOUT_SECONDS env var, defaulting to 3600s."""
    seconds = int(os.environ.get("STAGING_TIMEOUT_SECONDS", "3600"))
    return timedelta(seconds=seconds)
