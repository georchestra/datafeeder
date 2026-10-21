"""Resolve the dataset referenced by a JoinConfig to the table to join."""

from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN
from data_manipulation.models import IntegrityTransformation, JoinConfig, JoinTarget
from fastapi import HTTPException
from sqlmodel import Session

from src.core.config import get_data_schema
from src.core.security import AccessLevel, load_authorized_integrity_link
from src.services.georchestra import GeorchestraContext


def joins_geom(transformation: IntegrityTransformation | None) -> bool:
    """True when the join adds the geometry of the joined dataset.

    It then replaces the staging geometry, which must be excluded (see
    build_transformation_select).
    """
    join = transformation.join if transformation is not None else None
    return join is not None and DEFAULT_GEOMETRY_COLUMN in join.columns


def resolve_join_target(
    join: JoinConfig | None,
    geo_ctx: GeorchestraContext,
    session: Session,
    group_ids: list[str],
) -> JoinTarget | None:
    """Final table of the dataset joined by *join*, or ``None`` when there is no join.

    The caller must be able to read the joined dataset (METADATA_READ), the same
    rule as /integrity-links/joinable-tables and /joinable-columns.

    Raises:
        HTTPException 404/403: The joined dataset does not exist or is not readable.
        HTTPException 422: The joined dataset has no final table yet.
    """
    if join is None or not join.columns:
        return None
    try:
        link, _ = load_authorized_integrity_link(
            str(join.integrity_link_id), AccessLevel.METADATA_READ, geo_ctx, session, group_ids
        )
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=f"Joined dataset: {e.detail}")
    if not link.final_table_name:
        raise HTTPException(status_code=422, detail="Joined dataset has no final table yet")
    return JoinTarget(
        table_schema=get_data_schema(link.integrity_organization),
        table_name=link.final_table_name,
    )
