from enum import Enum
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class RuleType(str, Enum):
    DATA = "DATA"
    METADATA = "METADATA"


class RuleValue(str, Enum):
    READ = "READ"
    WRITE = "WRITE"


class IntegrityLinkRule(SQLModel, table=True):
    __tablename__: ClassVar[str] = "integrity_link_rules"  # type: ignore[misc]
    __table_args__ = {"schema": "datafeeder"}

    id: Optional[int] = Field(default=None, primary_key=True)
    integrity_link_id: Optional[UUID] = Field(
        default=None, foreign_key="datafeeder.integrity_link.id"
    )
    rule_type: RuleType
    rule_value: RuleValue = Field(default=RuleValue.READ)
    group_or_role: str = Field(max_length=255)


class UpsertRuleRequest(BaseModel):
    group_or_role: str
    rule_type: RuleType
    rule_value: RuleValue
