"""Tests for database identifier validators."""

import re

import pytest

from data_manipulation.validators import (
    IDENTIFIER_PATTERN,
    validate_postgres_identifier,
    validate_schema_name,
    validate_table_name,
)


class TestValidatePostgresIdentifier:
    """Test PostgreSQL identifier validation."""

    def test_valid_identifiers(self):
        """Test that valid identifiers pass validation."""
        valid_identifiers = [
            "my_table",
            "staging_abc123",
            "t",  # Single char
            "a" * 63,  # Max length
            "table_123_test",
            "schema_name",
            "test123",
        ]
        for identifier in valid_identifiers:
            assert validate_postgres_identifier(identifier) == identifier

    def test_invalid_identifiers(self):
        """Test that invalid identifiers raise ValueError."""
        invalid_identifiers = [
            "123_table",  # Starts with number
            "Table_Name",  # Uppercase
            "table-name",  # Hyphen
            "table.name",  # Dot
            "table name",  # Space
            "a" * 64,  # Too long
            "table; DROP TABLE users--",  # SQL injection attempt
            "table' OR '1'='1",  # SQL injection attempt
            'table" DROP SCHEMA public CASCADE--',  # SQL injection attempt
        ]
        for identifier in invalid_identifiers:
            with pytest.raises(ValueError):
                validate_postgres_identifier(identifier)

    def test_custom_identifier_type_in_error_message(self):
        """Test that custom identifier type appears in error messages."""
        with pytest.raises(ValueError, match="column name"):
            validate_postgres_identifier("INVALID", identifier_type="column name")

    def test_empty_string_error(self):
        """Test that empty string produces appropriate error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_postgres_identifier("")

    def test_whitespace_only_error(self):
        """Test that whitespace-only string produces appropriate error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_postgres_identifier("   ")


class TestValidateTableName:
    """Test table name validation."""

    def test_valid_table_names(self):
        """Test that valid table names pass validation."""
        valid_names = [
            "my_table",
            "staging_abc123",
            "t",  # Single char
            "a" * 63,  # Max length
            "table_123_test",
        ]
        for name in valid_names:
            assert validate_table_name(name) == name

    def test_invalid_table_names(self):
        """Test that invalid table names raise ValueError."""
        invalid_names = [
            "123_table",  # Starts with number
            "Table_Name",  # Uppercase
            "table-name",  # Hyphen
            "table.name",  # Dot
            "table name",  # Space
            "a" * 64,  # Too long
            "table; DROP TABLE users--",  # SQL injection attempt
            "table' OR '1'='1",  # SQL injection attempt
        ]
        for name in invalid_names:
            with pytest.raises(ValueError):
                validate_table_name(name)

    def test_empty_table_name_rejected(self):
        """Test that empty table names are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_table_name("")

        with pytest.raises(ValueError, match="cannot be empty"):
            validate_table_name("   ")

    def test_context_in_error_message(self):
        """Test that context appears in error messages."""
        with pytest.raises(ValueError, match="staging table name"):
            validate_table_name("INVALID", context="staging")

        with pytest.raises(ValueError, match="final table name"):
            validate_table_name("INVALID", context="final")

    def test_sql_injection_attempts_blocked(self):
        """Test that various SQL injection attempts are blocked."""
        sql_injection_attempts = [
            "table; DROP TABLE users--",
            "table' OR '1'='1",
            'table"; DROP SCHEMA public CASCADE--',
            "'; DELETE FROM staging_data--",
            "table UNION SELECT * FROM users--",
        ]
        for attempt in sql_injection_attempts:
            with pytest.raises(ValueError, match="Invalid.*table name"):
                validate_table_name(attempt)


class TestValidateSchemaName:
    """Test schema name validation."""

    def test_valid_schema_names(self):
        """Test that valid schema names pass validation."""
        valid_names = [
            "my_schema",
            "data",
            "staging",
            "s",
            "public123",
            "test_schema_123",
        ]
        for name in valid_names:
            assert validate_schema_name(name) == name

    def test_invalid_schema_names(self):
        """Test that invalid schema names raise ValueError."""
        invalid_names = [
            "Schema-Name",  # Hyphen
            "SCHEMA_NAME",  # Uppercase
            "123schema",  # Starts with number
        ]
        for name in invalid_names:
            with pytest.raises(ValueError):
                validate_schema_name(name)

    def test_empty_schema_name_rejected(self):
        """Test that empty schema names are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_schema_name("")

        with pytest.raises(ValueError, match="cannot be empty"):
            validate_schema_name("   ")

    def test_sql_injection_attempts_blocked(self):
        """Test that SQL injection attempts in schema names are blocked."""
        with pytest.raises(ValueError, match="Invalid schema name"):
            validate_schema_name("schema; DROP DATABASE prod--")


class TestIdentifierPattern:
    """Test the IDENTIFIER_PATTERN regex."""

    def test_pattern_matches_valid_identifiers(self):
        """Test that the regex pattern matches valid identifiers."""
        valid_identifiers = [
            "a",
            "abc",
            "abc_123",
            "table_name",
            "a" * 63,  # Max length
        ]
        for identifier in valid_identifiers:
            assert re.match(IDENTIFIER_PATTERN, identifier)

    def test_pattern_rejects_invalid_identifiers(self):
        """Test that the regex pattern rejects invalid identifiers."""
        invalid_identifiers = [
            "123",  # Starts with number
            "ABC",  # Uppercase
            "a-b",  # Hyphen
            "a.b",  # Dot
            "a b",  # Space
            "a" * 64,  # Too long
            "",  # Empty
        ]
        for identifier in invalid_identifiers:
            assert not re.match(IDENTIFIER_PATTERN, identifier)
