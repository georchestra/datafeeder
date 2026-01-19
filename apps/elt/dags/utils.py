from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.sdk import Variable
from sqlalchemy.engine import Engine


def get_datakern_pg_hook() -> PostgresHook:
    """Create and return a PostgresHook using Airflow Connection."""
    return PostgresHook("DATAKERN_PG")


def get_data_sql_engine() -> Engine:
    """Get SQLAlchemy engine from PostgresHook."""
    return PostgresHook("DATA_PG").get_data_sql_engine()


def get_final_schema() -> str:
    """Get the final schema from Airflow Variable, defaulting to 'data'."""
    return Variable.get("final_schema", "data")


def get_staging_schema() -> str:
    """Get the staging schema from Airflow Variable, defaulting to 'staging'."""
    return "staging"
