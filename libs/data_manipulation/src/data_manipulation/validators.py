"""Validation utilities for database identifiers."""

import re

# PostgreSQL identifier rules: max 63 chars, start with lowercase letter,
# contain only lowercase letters, numbers, underscores
IDENTIFIER_PATTERN = r"^[a-z][a-z0-9_]{0,62}$"


def validate_postgres_identifier(identifier: str, identifier_type: str = "identifier") -> str:
    """
    Validate PostgreSQL identifier (schema, table, column name) to prevent SQL injection.

    All PostgreSQL identifiers follow the same rules:
    - Start with a lowercase letter (a-z)
    - Contain only lowercase letters, numbers, and underscores
    - Maximum 63 characters

    Args:
        identifier: The identifier to validate
        identifier_type: Type of identifier for error messages (e.g., "table name", "schema name")

    Returns:
        The validated identifier

    Raises:
        ValueError: If the identifier contains invalid characters or is empty
    """
    if not identifier or not identifier.strip():
        raise ValueError(f"{identifier_type.capitalize()} cannot be empty")

    if not re.match(IDENTIFIER_PATTERN, identifier):
        raise ValueError(
            f"Invalid {identifier_type} '{identifier}'. "
            f"{identifier_type.capitalize()}s must start with a lowercase letter and contain only "
            "lowercase letters, numbers, and underscores (max 63 characters)."
        )
    return identifier


# Convenience aliases for better readability in code
def validate_table_name(table_name: str, context: str = "table") -> str:
    """Validate table name. Convenience wrapper around validate_postgres_identifier."""
    return validate_postgres_identifier(
        table_name, f"{context} table name" if context != "table" else "table name"
    )


def validate_schema_name(schema_name: str) -> str:
    """Validate schema name. Convenience wrapper around validate_postgres_identifier."""
    return validate_postgres_identifier(schema_name, "schema name")
