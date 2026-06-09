"""Service for AI-based metadata generation."""

from pathlib import Path

from ai.metadata_generator import generate_metadata
from ai.providers import get_llm
from sqlalchemy import inspect as sa_inspect

from src.core.config import Settings
from src.core.db import data_engine
from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.services.metadata_service import MetadataService

logger = get_logger()


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
        )

        inspector = sa_inspect(data_engine)
        columns: list[str] = [
            col["name"] for col in inspector.get_columns(final_table_name, schema=target_schema)
        ]

        result = generate_metadata(
            table_name=final_table_name,
            column_names=columns,
            llm=llm,
            title=integrity_link.integrity_title,
            system_prompt_path=Path(settings.AI_METADATA_SYSTEM_PROMPT_FILE)
            if settings.AI_METADATA_SYSTEM_PROMPT_FILE
            else None,
            human_prompt_path=Path(settings.AI_METADATA_HUMAN_PROMPT_FILE)
            if settings.AI_METADATA_HUMAN_PROMPT_FILE
            else None,
        )

        logger.info(
            f"AI metadata generated for IntegrityLink {integrity_link.id}: "
            f"topic={result.topic_category}, keywords={result.keywords}"
        )

        metadata_service = MetadataService(
            gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
            datadir_path=settings.DATADIR_PATH,
            credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
            verify_tls=False,
        )
        metadata_service.update_ai_metadata(
            metadata_uuid=str(integrity_link.metadata_id),
            abstract=result.abstract,
            keywords=result.keywords,
            topic_category=result.topic_category,
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
