from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import Variable
from sqlalchemy.engine import Engine


def get_postgres_hook() -> PostgresHook:
    """Create and return a PostgresHook using Airflow Connection."""
    return PostgresHook("CONN_POSTGIS")


def get_sqlalchemy_engine() -> Engine:
    """Get SQLAlchemy engine from PostgresHook."""
    hook = get_postgres_hook()
    return hook.get_sqlalchemy_engine()


def get_final_schema() -> str:
    """Get the final schema from Airflow Variable, defaulting to 'data'."""
    return Variable.get("final_schema", "data")


def get_staging_schema() -> str:
    """Get the staging schema from Airflow Variable, defaulting to 'staging'."""
    return "staging"
