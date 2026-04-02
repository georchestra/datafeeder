"""Database management utilities."""

import logging

from sqlalchemy import MetaData, Table, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchTableError
from sqlalchemy.schema import CreateSchema

from data_manipulation.logging import configure_logging
from data_manipulation.validators import validate_schema_name

logger = logging.getLogger(__name__)
configure_logging(logger)


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
    return inspect(engine).has_schema(schema_name)


def table_exists(engine: Engine, schema_name: str, table_name: str) -> bool:
    """
    Check if a database table exists in a given schema.

    Args:
        engine: SQLAlchemy engine instance
        schema_name: Name of the schema
        table_name: Name of the table to check

    Returns:
        bool: True if table exists, False otherwise
    """
    return inspect(engine).has_table(table_name, schema=schema_name)


def get_available_table_name(engine: Engine, schema_name: str, base_table_name: str) -> str | None:
    """
    Get an available table name by appending a numeric suffix if needed.

    Args:
        engine: SQLAlchemy engine instance
        schema_name: Schema where the table will be created
        base_table_name: Desired base name for the table)
    Returns:
        str: Available table name
    """

    max_attempts = 20

    for counter in range(max_attempts):
        if counter == 0:
            final_table_name = base_table_name
        else:
            suffix = f"_{counter}"
            truncate_length = 53 - len(suffix)
            final_table_name = base_table_name[:truncate_length] + suffix
        try:
            metadata = MetaData(schema=schema_name)
            Table(final_table_name, metadata, autoload_with=engine)
            logger.info("Table name exists, trying new name: %s", final_table_name)
        except NoSuchTableError:
            logger.info("Final table name available: %s", final_table_name)
            return final_table_name
