from typing import Literal

from data_manipulation.database import list_tables_by_schema
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from src.api.deps import GeorchestraContextDep
from src.core.config import SourceDatabase, get_settings
from src.core.db import get_source_engine
from src.core.logging import get_logger
from src.core.security import require_user
from src.services.georchestra import GeorchestraContext

logger = get_logger()

router = APIRouter(prefix="/source-databases", tags=["source-databases"])


class SourceDatabaseSummary(BaseModel):
    """A source database declared in SOURCE_DATABASES, without its connection details."""

    key: str
    type: Literal["copy", "direct_access"]
    label: str | None = None
    schema_name: str | None = None


class SourceSchema(BaseModel):
    """A schema of a source database, with its tables and views."""

    schema_name: str
    tables: list[str]


def _available_source_database(
    key: str, geo_ctx: GeorchestraContext
) -> tuple[SourceDatabase, Engine]:
    """Source database and its engine, 404 when it is unknown or not available to the user."""
    database = get_settings().SOURCE_DATABASES.get(key)
    if (
        database is None
        or not database.is_available_to(geo_ctx)
        or (engine := get_source_engine(key)) is None
    ):
        raise HTTPException(status_code=404, detail=f"Unknown source database '{key}'")
    return database, engine


@router.get(
    "/",
    response_model=list[SourceDatabaseSummary],
    summary="List source databases",
    description="Source databases declared in SOURCE_DATABASES without roles, or with at least "
    "one of the user's roles.",
)
def list_source_databases(geo_ctx: GeorchestraContextDep) -> list[SourceDatabaseSummary]:
    require_user(geo_ctx)
    return [
        SourceDatabaseSummary(key=key, type=db.type, label=db.label, schema_name=db.schema_name)
        for key, db in get_settings().SOURCE_DATABASES.items()
        if db.is_available_to(geo_ctx)
    ]


@router.get(
    "/{key}/tables",
    response_model=list[SourceSchema],
    summary="List the tables of a source database, by schema",
    description="Tables and views the connection user can access, system schemas excluded. "
    "Only for source databases available to the user's roles.",
)
def list_source_database_tables(key: str, geo_ctx: GeorchestraContextDep) -> list[SourceSchema]:
    require_user(geo_ctx)
    database, engine = _available_source_database(key, geo_ctx)

    try:
        schemas = list_tables_by_schema(engine)
    except SQLAlchemyError:
        logger.exception("Could not list the tables of source database '%s'", key)
        raise HTTPException(
            status_code=503, detail=f"Could not list the tables of source database '{key}'"
        ) from None

    allowed_schema = database.schema_name
    if allowed_schema:
        schemas = {name: tables for name, tables in schemas.items() if name == allowed_schema}
        if not schemas:
            logger.warning(
                "Configured schema '%s' of source database '%s' does not exist "
                "or has no table readable by the connection user",
                allowed_schema,
                key,
            )
    return [
        SourceSchema(schema_name=schema_name, tables=tables)
        for schema_name, tables in schemas.items()
    ]
