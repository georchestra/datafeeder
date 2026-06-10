"""Service for AI-based metadata generation."""

from pathlib import Path

from ai.metadata_generator import generate_metadata
from ai.providers import get_llm
from geoalchemy2 import Geometry  # type: ignore[import-untyped]
from sqlalchemy import MetaData, Table, func, select
from sqlalchemy import inspect as sa_inspect

from src.core.config import Settings
from src.core.db import data_engine
from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.services.metadata_service import MetadataService

logger = get_logger()


def _get_priority_keywords() -> list[str]:
    """Return the list of preferred keywords for AI metadata generation.

    Edit this list to steer the LLM towards the vocabulary used in your catalogue.
    These keywords are suggested as first choices; the LLM may still pick others.
    """
    return []


def _get_priority_topic_categories() -> list[str]:
    """Return the list of preferred ISO 19115 topic categories for AI metadata generation.

    Edit this list to restrict or prioritise the topic categories relevant to your catalogue.
    Valid values: "farming", "biota", "boundaries", "climatologyMeteorologyAtmosphere",
    "economy", "elevation", "environment", "geoscientificInformation", "health",
    "imageryBaseMapsEarthCover", "intelligenceMilitary", "inlandWaters", "location",
    "oceans", "planningCadastre", "society", "structure", "transportation",
    "utilitiesCommunication".
    """
    return []


def _get_sample_rows(
    table_name: str,
    schema: str,
    limit: int = 5,
) -> tuple[list[dict[str, object]], str | None]:
    """Fetch sample rows and bounding box from a PostGIS table.

    Returns a tuple of (sample_rows, bbox) where sample_rows excludes the geometry
    column and bbox is the ST_Extent string or None if unavailable.
    """
    sample_rows: list[dict[str, object]] = []
    bbox: str | None = None
    try:
        table_meta = MetaData(schema=schema)
        tbl = Table(table_name, table_meta, autoload_with=data_engine)
        with data_engine.connect() as conn:
            rows = conn.execute(select(tbl).limit(limit)).mappings().all()
            geom_cols = {col.name for col in tbl.c if isinstance(col.type, Geometry)}
            sample_rows = [{k: v for k, v in row.items() if k not in geom_cols} for row in rows]
            geom_col = next(iter(geom_cols), None)
            if geom_col:
                extent = conn.execute(select(func.ST_Extent(tbl.c[geom_col]))).scalar_one_or_none()
                if extent:
                    bbox = str(extent)
    except Exception as err:
        logger.warning("Could not fetch sample/bbox for table %s.%s: %s", schema, table_name, err)
    return sample_rows, bbox


def generate_ai_metadata(
    integrity_link: IntegrityLink,
    target_schema: str,
    settings: Settings,
) -> None:
    """Generate AI metadata for an integrity link and update GeoNetwork.

    Soft failure: logs a warning on error, never raises.
    No-op if AI_ENABLED=False or if the integrity link has no metadata_id.
    """
    if not settings.AI_ENABLED:
        logger.info("AI metadata generation is disabled (AI_ENABLED=False) — skipping")
        return

    if not integrity_link.metadata_id:
        logger.info(
            f"IntegrityLink {integrity_link.id} has no metadata_id yet — skipping AI generation"
        )
        return

    final_table_name = integrity_link.final_table_name
    if not final_table_name:
        logger.warning(
            f"IntegrityLink {integrity_link.id} has no final_table_name — skipping AI generation"
        )
        return

    try:
        llm = get_llm(
            provider=settings.AI_PROVIDER,  # type: ignore[arg-type]
            model=settings.AI_MODEL or None,
            api_key=settings.AI_API_KEY or None,
            base_url=settings.AI_BASE_URL or None,
            think=False,
        )

        inspector = sa_inspect(data_engine)
        columns: list[str] = [
            col["name"] for col in inspector.get_columns(final_table_name, schema=target_schema)
        ]

        # Fetch 5 sample rows and bbox from the final table
        sample_rows, bbox = _get_sample_rows(final_table_name, target_schema)

        result = generate_metadata(
            table_name=final_table_name,
            column_names=columns,
            llm=llm,
            title=integrity_link.integrity_title,
            sample_rows=sample_rows or None,
            bbox=bbox,
            priority_keywords=_get_priority_keywords() or None,
            priority_topic_categories=_get_priority_topic_categories() or None,
            system_prompt_path=Path(settings.AI_METADATA_SYSTEM_PROMPT_FILE)
            if settings.AI_METADATA_SYSTEM_PROMPT_FILE
            else None,
            human_prompt_path=Path(settings.AI_METADATA_HUMAN_PROMPT_FILE)
            if settings.AI_METADATA_HUMAN_PROMPT_FILE
            else None,
        )

        logger.info(
            f"AI metadata generated for IntegrityLink {integrity_link.id}: "
            f"topics={result.topic_categories}, keywords={result.keywords}"
        )

        metadata_service = MetadataService(
            gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
            datadir_path=settings.DATADIR_PATH,
            credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
            verify_tls=False,
        )
        metadata_service.update_ai_metadata(
            metadata_uuid=str(integrity_link.metadata_id),
            title=result.title,
            abstract=result.abstract,
            keywords=result.keywords,
            topic_categories=result.topic_categories,
        )
        logger.info(
            f"GeoNetwork metadata updated with AI fields for IntegrityLink {integrity_link.id}"
        )
    except Exception as e:
        logger.warning(
            "Failed to generate or update AI metadata for IntegrityLink %s: %s",
            integrity_link.id,
            e,
            exc_info=True,
        )
        raise
