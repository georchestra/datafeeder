"""Database management utilities."""

from sqlalchemy import text
from sqlalchemy.engine import Engine


def create_schema(engine: Engine, schema_name: str) -> None:
    """
    Create a database schema if it doesn't already exist.

    Args:
        engine: SQLAlchemy engine instance
        schema_name: Name of the schema to create

    Raises:
        Exception: If schema creation fails
    """
    if not schema_exists(engine, schema_name):
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA {schema_name}"))
            conn.commit()


def schema_exists(engine: Engine, schema_name: str) -> bool:
    """
    Check if a database schema exists.

    Args:
        engine: SQLAlchemy engine instance
        schema_name: Name of the schema to check

    Returns:
        bool: True if schema exists, False otherwise
    """
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_name"
            ),
            {"schema_name": schema_name},
        )
        return result.fetchone() is not None
