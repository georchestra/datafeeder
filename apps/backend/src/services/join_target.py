"""Resolve the dataset referenced by a JoinConfig to the table to join."""

from uuid import UUID

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN
from data_manipulation.database import table_exists
from data_manipulation.models import IntegrityTransformation, JoinConfig, JoinTarget
from fastapi import HTTPException
from sqlalchemy import ColumnElement, and_
from sqlmodel import Session, col, select

from src.core.config import get_data_schema
from src.core.db import data_engine
from src.models.integrity_link import IntegrityLink

# Generic on purpose: the joined dataset may be one the caller cannot otherwise see.
JOIN_UNAVAILABLE = "i18nerror.join.unavailable"


def joinable_condition() -> ColumnElement[bool]:
    """A dataset can be joined when it is a reference dataset with a final table.

    Any user may join it, whatever its publication or access rules. The join reads
    the final table, so a dataset without one cannot be joined, whatever its import
    type: direct access or prefilled (data outside the data database), empty, or not
    processed yet. The table must also exist in the data database (see
    get_join_target). Scheduled runs apply the same rule in
    apps/elt/dags/process-dag-generator.py.
    """
    return and_(
        col(IntegrityLink.is_reference_dataset),
        col(IntegrityLink.final_table_name).is_not(None),
    )


def get_join_target(integrity_link_id: UUID, session: Session) -> JoinTarget | None:
    """Final table of the dataset *integrity_link_id*, or ``None`` when it cannot be joined."""
    row = session.exec(
        select(
            col(IntegrityLink.integrity_organization), col(IntegrityLink.final_table_name)
        ).where(col(IntegrityLink.id) == integrity_link_id, joinable_condition())
    ).first()
    if row is None:
        return None
    organization, table_name = row
    if not table_name:  # excluded by joinable_condition
        return None
    schema = get_data_schema(organization)
    if not table_exists(data_engine, schema, table_name):
        return None
    return JoinTarget(table_schema=schema, table_name=table_name)


def joins_geom(transformation: IntegrityTransformation | None) -> bool:
    """True when the join adds the geometry of the joined dataset.

    It then replaces the staging geometry, which must be excluded (see
    build_transformation_select).
    """
    join = transformation.join if transformation is not None else None
    return join is not None and any(
        col.original_name == DEFAULT_GEOMETRY_COLUMN for col in join.columns
    )


def resolve_join_target(join: JoinConfig | None, session: Session) -> JoinTarget | None:
    """Final table of the dataset joined by *join*, or ``None`` when there is no join.

    Raises:
        HTTPException 422: The joined dataset cannot be joined (see joinable_condition).
    """
    if join is None or not join.columns:
        return None
    target = get_join_target(join.integrity_link_id, session)
    if target is None:
        raise HTTPException(status_code=422, detail=JOIN_UNAVAILABLE)
    return target
