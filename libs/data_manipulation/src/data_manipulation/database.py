"""Database management utilities."""

import logging

from sqlalchemy import MetaData, Table, text
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
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema_name"
            ),
            {"schema_name": schema_name},
        )
        return result.fetchone() is not None


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

    final_table_name = base_table_name
    counter = 1
    max_attempts = 20
    while counter < max_attempts:
        try:
            metadata = MetaData(schema=schema_name)
            Table(final_table_name, metadata, autoload_with=engine)
            suffix = f"_{counter}"
            truncate_length = (
                53 - len(suffix)
            )  # PostgreSQL max table name length is 63 but index sometimes append _geometry so we leave some buffer
            final_table_name = final_table_name[:truncate_length] + suffix
            counter += 1
            logger.info("Final table name exists, trying new name: %s", final_table_name)
        except NoSuchTableError:
            logger.info("Final table name available: %s", final_table_name)
            break
    else:
        # Reached max attempts
        final_table_name = None

    return final_table_name
