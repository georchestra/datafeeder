from datetime import datetime, timedelta, timezone
from typing import Any, ClassVar, Optional
from uuid import UUID

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class IntegrityLink(SQLModel, table=True):
    __tablename__: ClassVar[str] = "integrity_link"  # type: ignore[misc]
    __table_args__ = {"schema": "datakern"}

    id: Optional[UUID] = Field(
        default=None, primary_key=True, sa_column_kwargs={"server_default": "gen_random_uuid()"}
    )
    data_id: Optional[str] = Field(default=None, max_length=256)
    metadata_id: Optional[str] = Field(default=None, max_length=256)
    integrity_owner: str = Field(max_length=256)
    integrity_organization: str
    integrity_transformation: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    staging_table_name: str | None = Field(default=None, max_length=63)
    last_staging_retrieved_at: Optional[datetime] = None
    final_table_name: Optional[str] = Field(default=None, max_length=63, unique=True)
    retrieve_time: Optional[timedelta] = None
    schedule: Optional[str] = Field(default=None, max_length=10)
    schedule_enabled: bool = Field(default=False)
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column_kwargs={"server_default": "current_timestamp"},
    )
