"""Database management utilities."""

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateSchema

from data_manipulation.validators import validate_schema_name


def create_schema(engine: Engine, schema_name: str) -> None:
    """
    Create a database schema if it doesn't already exist.

    Args:
        engine: SQLAlchemy engine instance
        schema_name: Name of the schema to create

    Raises:
        ValueError: If schema name contains invalid characters
        Exception: If schema creation fails
    """
    # Validate schema name to prevent SQL injection (defense in depth)
    validated_schema_name = validate_schema_name(schema_name)

    if not schema_exists(engine, validated_schema_name):
        with engine.connect() as conn:
            # Use SQLAlchemy's DDL construct for safe schema creation
            # This properly quotes the identifier and prevents SQL injection
            conn.execute(CreateSchema(validated_schema_name, if_not_exists=True))
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
