"""LLM-powered metadata generation routes."""

from typing import Any, Literal

from ai.metadata_generator import GeneratedMetadata
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api.deps import DatafeederSessionDep, GeorchestraContextDep, GroupIdsDep
from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.security import AccessLevel, load_authorized_integrity_link
from src.services.ai_service import generate_metadata_suggestions

logger = get_logger()

router = APIRouter(prefix="/llm", tags=["LLM"])


class GenerateMetadataRequest(BaseModel):
    """Request body for AI metadata generation."""

    mode: Literal["regenerate", "rewrite"] = "regenerate"
    data_source: Literal["staging", "final"] = "staging"
    current_values: dict[str, Any] | None = None


@router.post("/generate_metadata/{intlink_id}", response_model=GeneratedMetadata)
def generate_metadata_for_integrity_link(
    intlink_id: str,
    body: GenerateMetadataRequest,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    group_ids: GroupIdsDep,
) -> GeneratedMetadata:
    """Generate AI-powered metadata suggestions for an integrity link.

    Args:
        intlink_id: Integrity link ID (UUID string)
        session: Database session dependency
        geo_ctx: geOrchestra security context
        group_ids: User's group IDs

    Returns:
        GeneratedMetadata with suggested title, abstract, keywords, topic categories,
        attribute descriptions, and temporal extent.

    Raises:
        HTTPException: 403 if user lacks access, 404 if integrity link not found,
                      400 if AI is disabled or staging table not available,
                      500 on internal errors
    """
    logger.info(f"[LLM] Received request to generate metadata for integrity link: {intlink_id}")
    settings = get_settings()

    logger.info(f"[LLM] AI_ENABLED={settings.AI_ENABLED}")

    try:
        # Load and authorize integrity link
        logger.info(f"[LLM] Loading and authorizing integrity link {intlink_id}...")
        integrity_link, _ = load_authorized_integrity_link(
            intlink_id, AccessLevel.METADATA_READ, geo_ctx, session, group_ids
        )
        logger.info(
            f"[LLM] Integrity link loaded: staging_table={integrity_link.staging_table_name}"
        )

    except Exception as e:
        logger.error(f"[LLM] Failed to load integrity link {intlink_id}: {e}", exc_info=True)
        raise

    try:
        # Generate metadata suggestions using the AI service
        logger.info(f"[LLM] Calling generate_metadata_suggestions for {intlink_id}...")
        result = generate_metadata_suggestions(
            integrity_link,
            settings,
            data_source=body.data_source,
            mode=body.mode,
            current_values=body.current_values,
        )
        logger.info(f"[LLM] Successfully generated metadata for {intlink_id}")
        return result

    except ValueError as e:
        # Validation errors (AI disabled, no staging table, etc.)
        logger.warning(f"[LLM] Validation error for {intlink_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Re-raise HTTP exceptions (authorization, not found)
        raise
    except Exception as e:
        logger.error(f"[LLM] Failed to generate AI metadata for {intlink_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate AI metadata: {str(e)}",
        )
