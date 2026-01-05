"""Tests for IntegrityLink model validators.

Note: SQLModel with table=True bypasses validation during direct instantiation
for performance reasons. Validators are triggered when using model_validate(),
which is how FastAPI creates model instances from request data.
"""

import pytest
from pydantic import ValidationError

from src.models.integrity_link import IntegrityLink


class TestIntegrityLinkValidators:
    """Test IntegrityLink Pydantic validators using model_validate()."""

    def test_valid_table_names_accepted(self):
        """Test that valid table names are accepted."""
        link = IntegrityLink.model_validate(
            {
                "integrity_owner": "testuser",
                "integrity_organization": "testorg",
                "staging_table_name": "staging_abc123",
                "final_table_name": "final_xyz789",
            }
        )
        assert link.staging_table_name == "staging_abc123"
        assert link.final_table_name == "final_xyz789"

    def test_invalid_staging_table_name_rejected(self):
        """Test that invalid staging table names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IntegrityLink.model_validate(
                {
                    "integrity_owner": "testuser",
                    "integrity_organization": "testorg",
                    "staging_table_name": "INVALID_NAME",  # Uppercase
                }
            )
        assert "staging" in str(exc_info.value).lower()

    def test_invalid_final_table_name_rejected(self):
        """Test that invalid final table names are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            IntegrityLink.model_validate(
                {
                    "integrity_owner": "testuser",
                    "integrity_organization": "testorg",
                    "staging_table_name": "staging_test",
                    "final_table_name": "final-table",  # Hyphen
                }
            )
        assert "final" in str(exc_info.value).lower()

    def test_sql_injection_attempts_rejected(self):
        """Test that SQL injection attempts in table names are rejected."""
        injection_attempts = [
            "table; DROP TABLE users--",
            "table' OR '1'='1",
            'table"; DROP SCHEMA public CASCADE--',
        ]
        for attempt in injection_attempts:
            with pytest.raises(ValidationError):
                IntegrityLink.model_validate(
                    {
                        "integrity_owner": "testuser",
                        "integrity_organization": "testorg",
                        "staging_table_name": attempt,
                    }
                )

    def test_final_table_name_optional(self):
        """Test that final_table_name can be None."""
        link = IntegrityLink.model_validate(
            {
                "integrity_owner": "testuser",
                "integrity_organization": "testorg",
                "staging_table_name": "staging_test",
                "final_table_name": None,
            }
        )
        assert link.final_table_name is None

    def test_table_name_max_length_enforced(self):
        """Test that table names exceeding 63 characters are rejected."""
        too_long_name = "a" * 64  # 64 characters (exceeds PostgreSQL limit of 63)
        with pytest.raises(ValidationError):
            IntegrityLink.model_validate(
                {
                    "integrity_owner": "testuser",
                    "integrity_organization": "testorg",
                    "staging_table_name": too_long_name,
                }
            )

    def test_table_name_starts_with_number_rejected(self):
        """Test that table names starting with numbers are rejected."""
        with pytest.raises(ValidationError):
            IntegrityLink.model_validate(
                {
                    "integrity_owner": "testuser",
                    "integrity_organization": "testorg",
                    "staging_table_name": "123_invalid",
                }
            )

    def test_table_name_with_special_chars_rejected(self):
        """Test that table names with special characters are rejected."""
        invalid_names = [
            "table-name",  # Hyphen
            "table.name",  # Dot
            "table name",  # Space
            "table@name",  # Special char
            "table#name",  # Special char
        ]
        for invalid_name in invalid_names:
            with pytest.raises(ValidationError):
                IntegrityLink.model_validate(
                    {
                        "integrity_owner": "testuser",
                        "integrity_organization": "testorg",
                        "staging_table_name": invalid_name,
                    }
                )

    def test_existing_organization_validator_still_works(self):
        """Test that the existing organization validator still works."""
        # Valid organization
        link = IntegrityLink.model_validate(
            {
                "integrity_owner": "testuser",
                "integrity_organization": "validorg",
                "staging_table_name": "staging_test",
            }
        )
        assert link.integrity_organization == "validorg"

        # Invalid organization (uppercase)
        with pytest.raises(ValidationError) as exc_info:
            IntegrityLink.model_validate(
                {
                    "integrity_owner": "testuser",
                    "integrity_organization": "INVALID_ORG",
                    "staging_table_name": "staging_test",
                }
            )
        assert "organization" in str(exc_info.value).lower()
