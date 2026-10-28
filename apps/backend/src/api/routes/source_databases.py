from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import GeorchestraContextDep
from src.core.config import get_settings

router = APIRouter(prefix="/source-databases", tags=["source-databases"])


class SourceDatabaseSummary(BaseModel):
    """A source database declared in SOURCE_DATABASES, without its connection details."""

    key: str
    type: Literal["copy", "direct_access"]
    label: str | None = None


@router.get(
    "/",
    response_model=list[SourceDatabaseSummary],
    summary="List source databases",
    description="Administrators only. Source databases declared in SOURCE_DATABASES.",
)
def list_source_databases(geo_ctx: GeorchestraContextDep) -> list[SourceDatabaseSummary]:
    if not geo_ctx.is_administrator():
        raise HTTPException(status_code=403, detail="Administrator role required")
    return [
        SourceDatabaseSummary(key=key, type=db.type, label=db.label)
        for key, db in get_settings().SOURCE_DATABASES.items()
    ]
