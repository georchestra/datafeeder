from typing import Literal

from data_manipulation.database import list_tables_by_schema
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from src.api.deps import GeorchestraContextDep
from src.core.config import get_settings
from src.core.db import get_source_engine
from src.core.logging import get_logger
from src.core.security import require_administrator

logger = get_logger()

router = APIRouter(prefix="/source-databases", tags=["source-databases"])


class SourceDatabaseSummary(BaseModel):
    """A source database declared in SOURCE_DATABASES, without its connection details."""

    key: str
    type: Literal["copy", "direct_access"]
    label: str | None = None


class SourceSchema(BaseModel):
    """A schema of a source database, with its tables and views."""

    schema_name: str
    tables: list[str]


@router.get(
    "/",
    response_model=list[SourceDatabaseSummary],
    summary="List source databases",
    description="Administrators only. Source databases declared in SOURCE_DATABASES.",
)
def list_source_databases(geo_ctx: GeorchestraContextDep) -> list[SourceDatabaseSummary]:
    require_administrator(geo_ctx)
    return [
        SourceDatabaseSummary(key=key, type=db.type, label=db.label)
        for key, db in get_settings().SOURCE_DATABASES.items()
    ]


@router.get(
    "/{key}/tables",
    response_model=list[SourceSchema],
    summary="List the tables of a source database, by schema",
    description="Administrators only. Tables and views the connection user can access, "
    "system schemas excluded.",
)
def list_source_database_tables(key: str, geo_ctx: GeorchestraContextDep) -> list[SourceSchema]:
    require_administrator(geo_ctx)
    engine = get_source_engine(key)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Unknown source database '{key}'")

    try:
        schemas = list_tables_by_schema(engine)
    except SQLAlchemyError:
        logger.exception("Could not list the tables of source database '%s'", key)
        raise HTTPException(
            status_code=503, detail=f"Could not list the tables of source database '{key}'"
        ) from None

    return [
        SourceSchema(schema_name=schema_name, tables=tables)
        for schema_name, tables in schemas.items()
    ]
