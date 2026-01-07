from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Optional
from uuid import UUID

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
    integrity_organization: str
    integrity_transformation: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    source_import_type: ImportType
    source_url: Optional[str] = None
    source_file_name: Optional[str] = None
    source_file_type: Optional[FileType] = None
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
