from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.api.deps import GeorchestraContextDep
from src.core.config import get_settings
from src.core.db import get_source_engine
from src.core.logging import get_logger
from src.services.georchestra import GeorchestraContext

logger = get_logger()

router = APIRouter(prefix="/source-databases", tags=["source-databases"])

# information_schema.tables only lists the tables and views the connection user has a privilege on.
# Tables and views created by an extension (e.g. PostGIS spatial_ref_sys, geometry_columns) are left
# out: they are internal objects, not data.
_LIST_TABLES_QUERY = text(
    """
    SELECT t.table_schema, t.table_name
    FROM information_schema.tables t
    WHERE t.table_schema NOT IN ('information_schema', 'pg_catalog')
      AND t.table_schema NOT LIKE 'pg\\_%'
      AND NOT EXISTS (
        SELECT 1
        FROM pg_depend d
        JOIN pg_class c ON c.oid = d.objid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE d.classid = 'pg_class'::regclass
          AND d.deptype = 'e'
          AND n.nspname = t.table_schema
          AND c.relname = t.table_name
      )
    ORDER BY t.table_schema, t.table_name
    """
)


class SourceDatabaseSummary(BaseModel):
    """A source database declared in SOURCE_DATABASES, without its connection details."""

    key: str
    type: Literal["copy", "direct_access"]
    label: str | None = None


class SourceSchema(BaseModel):
    """A schema of a source database, with its tables and views."""

    schema_name: str
    tables: list[str]


def _require_administrator(geo_ctx: GeorchestraContext) -> None:
    if not geo_ctx.is_administrator():
        raise HTTPException(status_code=403, detail="Administrator role required")


@router.get(
    "/",
    response_model=list[SourceDatabaseSummary],
    summary="List source databases",
    description="Administrators only. Source databases declared in SOURCE_DATABASES.",
)
def list_source_databases(geo_ctx: GeorchestraContextDep) -> list[SourceDatabaseSummary]:
    _require_administrator(geo_ctx)
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
    _require_administrator(geo_ctx)
    engine = get_source_engine(key)
    if engine is None:
        raise HTTPException(status_code=404, detail=f"Unknown source database '{key}'")

    try:
        with engine.connect() as conn:
            rows = conn.execute(_LIST_TABLES_QUERY).all()
    except SQLAlchemyError:
        logger.exception("Could not list the tables of source database '%s'", key)
        raise HTTPException(
            status_code=503, detail=f"Source database '{key}' is unreachable"
        ) from None

    schemas: dict[str, list[str]] = {}
    for schema, table in rows:
        schemas.setdefault(schema, []).append(table)
    return [
        SourceSchema(schema_name=schema_name, tables=tables)
        for schema_name, tables in schemas.items()
    ]
