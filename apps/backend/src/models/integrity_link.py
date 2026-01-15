import re
from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Optional
from uuid import UUID

from data_manipulation.validators import validate_table_name
from pydantic import field_validator
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from src.models.data_import import FileType, ImportType


class IntegrityLink(SQLModel, table=True):
    __tablename__: ClassVar[str] = "integrity_link"  # type: ignore[misc]
    __table_args__ = {"schema": "datakern"}

    id: Optional[UUID] = Field(
        default=None, primary_key=True, sa_column_kwargs={"server_default": "gen_random_uuid()"}
    )
    data_id: Optional[str] = Field(default=None, max_length=256)
    metadata_id: Optional[str] = Field(default=None, max_length=256)
    integrity_title: Optional[str] = Field(default=None, max_length=256)
    integrity_owner: str = Field(max_length=256)
    integrity_organization: str = Field(max_length=63)
    integrity_transformation: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    source_import_type: ImportType
    source_url: Optional[str] = None
    source_file_name: Optional[str] = None
    source_file_type: Optional[FileType] = None
    source_username: Optional[str] = None
    source_password_encrypted: Optional[str] = None
    source_auth_enabled: bool = Field(default=False)
    staging_table_name: str = Field(max_length=63)
    staging_retrieve_time: Optional[timedelta] = None
    final_table_name: Optional[str] = Field(default=None, max_length=63, unique=True)
    last_retrieval_timestamp: Optional[datetime] = None
    schedule: Optional[str] = Field(default=None, max_length=10)
    schedule_enabled: bool = Field(default=False)
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"server_default": "current_timestamp"},
    )

    @field_validator("integrity_organization")
    @classmethod
    def validate_organization(cls, v: str) -> str:
        """
        Validate organization name to prevent SQL injection.

        Organization names are used as PostgreSQL schema names, so they must
        follow strict naming rules to prevent SQL injection attacks.

        Args:
            v: The organization name to validate

        Returns:
            The validated organization name

        Raises:
            ValueError: If the organization name contains invalid characters
        """
        if not re.match(r"^[a-z][a-z0-9_]{0,62}$", v):
            raise ValueError(
                f"Invalid organization name '{v}'. "
                "Organization names must start with a lowercase letter and contain only "
                "lowercase letters, numbers, and underscores (max 63 characters)."
            )
        return v

    @field_validator("staging_table_name")
    @classmethod
    def validate_staging_table_name(cls, v: str) -> str:
        """
        Validate staging table name to prevent SQL injection.

        Staging table names are used in SQL queries, so they must follow
        strict naming rules to prevent SQL injection attacks.

        Args:
            v: The staging table name to validate

        Returns:
            The validated staging table name

        Raises:
            ValueError: If the staging table name contains invalid characters
        """
        return validate_table_name(v, context="staging")

    @field_validator("final_table_name")
    @classmethod
    def validate_final_table_name(cls, v: str | None) -> str | None:
        """
        Validate final table name to prevent SQL injection.

        Final table names are used in SQL queries, so they must follow
        strict naming rules to prevent SQL injection attacks.

        Args:
            v: The final table name to validate (can be None)

        Returns:
            The validated final table name or None

        Raises:
            ValueError: If the final table name contains invalid characters
        """
        if v is None:
            return v
        return validate_table_name(v, context="final")
