"""Validation utilities for database identifiers."""

import re

from data_manipulation.constants import PG_IDENTIFIER_MAX_LENGTH

# PostgreSQL identifier rules: start with lowercase letter, contain only
# lowercase letters, numbers, underscores. The length bound is enforced
# separately so callers can tighten it (e.g. PostGIS table names must leave
# room for the auto-created spatial index suffix).
IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_]*$"


def validate_postgres_identifier(
    identifier: str,
    identifier_type: str = "identifier",
    max_length: int = PG_IDENTIFIER_MAX_LENGTH,
) -> str:
    """
    Validate PostgreSQL identifier (schema, table, column name) to prevent SQL injection.

    All PostgreSQL identifiers follow the same rules:
    - Start with a lowercase letter (a-z)
    - Contain only lowercase letters, numbers, and underscores
    - Maximum ``max_length`` characters (defaults to PostgreSQL's 63-char cap)

    Args:
        identifier: The identifier to validate
        identifier_type: Type of identifier for error messages (e.g., "table name", "schema name")
        max_length: Maximum allowed length; tighten below 63 when downstream
            usage requires headroom (e.g. PostGIS spatial index suffix).

    Returns:
        The validated identifier

    Raises:
        ValueError: If the identifier contains invalid characters, is empty, or exceeds max_length
    """
    if not identifier or not identifier.strip():
        raise ValueError(f"{identifier_type.capitalize()} cannot be empty")

    if not re.match(IDENTIFIER_PATTERN, identifier):
        raise ValueError(
            f"Invalid {identifier_type} '{identifier}'. "
            f"{identifier_type.capitalize()}s must start with a lowercase letter and contain only "
            "lowercase letters, numbers, and underscores."
        )

    if len(identifier) > max_length:
        raise ValueError(
            f"Invalid {identifier_type} '{identifier}': length {len(identifier)} exceeds "
            f"maximum of {max_length} characters."
        )

    return identifier


# Convenience aliases for better readability in code
def validate_table_name(
    table_name: str,
    context: str = "table",
    max_length: int = PG_IDENTIFIER_MAX_LENGTH,
) -> str:
    """Validate table name. Convenience wrapper around validate_postgres_identifier."""
    return validate_postgres_identifier(
        table_name,
        f"{context} table name" if context != "table" else "table name",
        max_length=max_length,
    )


def validate_schema_name(schema_name: str) -> str:
    """Validate schema name. Convenience wrapper around validate_postgres_identifier."""
    return validate_postgres_identifier(schema_name, "schema name")
