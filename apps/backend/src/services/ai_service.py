"""Service for AI-based metadata generation."""

from pathlib import Path
from typing import Any, Literal

import geopandas as gpd
import requests
from ai.metadata_generator import generate_metadata
from ai.metadata_generator_models import GeneratedMetadata, LlmMetadataMode
from ai.providers import get_llm
from ai.utils import pg_type_to_iso19110  # type: ignore[import-untyped]
from data_manipulation.ingestion import read_and_transform_data
from data_manipulation.models import IntegrityTransformation
from sqlalchemy import inspect as sa_inspect

from src.core.config import Settings, get_data_schema, get_staging_schema
from src.core.db import data_engine
from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.services.metadata_service import MetadataService

logger = get_logger()


def _fetch_thesaurus_keywords(
    gn_api_url: str,
    thesaurus_ids: list[str],
    credentials: tuple[str, str],
    max_results: int = 200,
    verify_tls: bool = True,
) -> list[str]:
    """Fetch keyword labels from one or more GeoNetwork thesauruses.

    Uses the GeoNetwork REST API: GET /registries/vocabularies/{id}/keywords

    Args:
        gn_api_url: GeoNetwork API base URL (e.g. http://host/geonetwork/srv/api)
        thesaurus_ids: List of thesaurus identifiers (e.g. "external.theme.inspire-theme")
        credentials: (username, password) tuple for basic auth
        max_results: Maximum number of keywords to fetch per thesaurus

    Returns:
        Deduplicated list of keyword label strings.
    """
    keywords: list[str] = []
    for thesaurus_id in thesaurus_ids:
        url = f"{gn_api_url}/registries/vocabularies/{thesaurus_id}/keywords"
        try:
            resp = requests.get(
                url,
                auth=credentials,
                params={"maxResults": max_results, "lang": "fre,eng"},
                timeout=10,
                verify=verify_tls,
            )
            resp.raise_for_status()
            data = resp.json()
            # Response is a list of keyword objects with a "values" dict keyed by language
            for item in data:
                values: dict[str, str] = item.get("values", {})
                label = values.get("fre") or values.get("eng") or next(iter(values.values()), None)
                if label:
                    keywords.append(label)
        except Exception as err:
            logger.warning("Could not fetch thesaurus %s from GeoNetwork: %s", thesaurus_id, err)
    # Deduplicate while preserving order
    seen: set[str] = set()
    return [k for k in keywords if not (k in seen or seen.add(k))]  # type: ignore[func-returns-value]


def _fetch_keywords_from_geonetwork(
    gn_api_url: str,
    credentials: tuple[str, str],
    max_results: int = 200,
    verify_tls: bool = True,
) -> list[str]:
    """Fetch keyword labels from all GeoNetwork thesauruses.

    Auto-discovers all available thesauruses via GET /registries/vocabularies,
    then fetches keywords for each.

    Args:
        gn_api_url: GeoNetwork API base URL
        credentials: (username, password) tuple for basic auth
        max_results: Maximum keywords per thesaurus

    Returns:
        Deduplicated list of keyword label strings.
    """
    thesaurus_ids: list[str] = []
    try:
        resp = requests.get(
            f"{gn_api_url}/registries/vocabularies",
            auth=credentials,
            headers={"Accept": "application/json"},
            timeout=10,
            verify=verify_tls,
        )
        resp.raise_for_status()
        thesaurus_ids = [t["key"] for t in resp.json() if "key" in t]
        logger.info("Found %d thesauruses in GeoNetwork", len(thesaurus_ids))
    except Exception as err:
        logger.warning("Could not list GeoNetwork thesauruses: %s", err)
        return []

    # Step 2: fetch keywords for each thesaurus
    return _fetch_thesaurus_keywords(
        gn_api_url,
        thesaurus_ids,
        credentials,
        max_results,
        verify_tls=verify_tls,
    )


def _fetch_topic_categories_from_geonetwork(
    gn_api_url: str,
    credentials: tuple[str, str],
    verify_tls: bool = True,
) -> list[str]:
    """Fetch ISO 19115 MD_TopicCategoryCode values from GeoNetwork's registries API.

    Uses: GET /registries/entries?registry={codelist_url}
    Returns an empty list if the endpoint is unavailable.

    Args:
        gn_api_url: GeoNetwork API base URL (e.g. http://host/geonetwork/srv/api)
        credentials: (username, password) tuple for basic auth

    Returns:
        List of ISO 19115 topic category code strings.
    """
    registry_url = (
        "http://standards.iso.org/iso/19115/resources/Codelists/cat/codelists.xml"
        "#MD_TopicCategoryCode"
    )
    try:
        resp = requests.get(
            f"{gn_api_url}/registries/entries",
            auth=credentials,
            headers={"Accept": "application/json"},
            params={"registry": registry_url, "lang": "fre", "rows": 50},
            timeout=10,
            verify=verify_tls,
        )
        resp.raise_for_status()
        data = resp.json()
        categories = [item["value"] for item in data if "value" in item]
        if categories:
            logger.info("Fetched %d topic categories from GeoNetwork", len(categories))
            return categories
    except Exception as err:
        logger.warning(
            "Could not fetch topic categories from GeoNetwork (%s), returning an empty list", err
        )
    return []


def _get_sample_from_staging(
    integrity_link: IntegrityLink,
    limit: int = 5,
) -> tuple[list[str], dict[str, str], list[dict[str, object]], str | None]:
    """Fetch column info and sample rows from the staging table with transformations applied.

    Returns:
        Tuple of (columns, column_types, sample_rows, bbox) where:
        - columns: column names after transformation (excluded and geometry columns omitted)
        - column_types: mapping of display column name → ISO 19110 type string
        - sample_rows: up to `limit` rows as dicts (geometry excluded)
        - bbox: bounding box string or None
    """
    staging_table_name = integrity_link.staging_table_name
    if not staging_table_name:
        return [], {}, [], None

    staging_schema = get_staging_schema()

    config: IntegrityTransformation | None = None
    if integrity_link.integrity_transformation:
        try:
            config = IntegrityTransformation.model_validate(integrity_link.integrity_transformation)
        except Exception as err:
            logger.warning("Could not parse transformation config: %s", err)

    # Get staging column types from DB schema
    staging_col_types: dict[str, str] = {}
    try:
        inspector = sa_inspect(data_engine)
        raw_cols = inspector.get_columns(staging_table_name, schema=staging_schema)
        staging_col_types = {col["name"]: pg_type_to_iso19110(str(col["type"])) for col in raw_cols}
    except Exception as err:
        logger.warning("Could not inspect staging table %s: %s", staging_table_name, err)

    # Compute output column names and types (post-transformation, geometry excluded)
    if config and config.columns:
        columns: list[str] = []
        column_types: dict[str, str] = {}
        for col_cfg in config.columns:
            if col_cfg.excluded or col_cfg.original_name == "geom":
                continue
            display_name = col_cfg.new_name or col_cfg.original_name
            columns.append(display_name)
            column_types[display_name] = staging_col_types.get(col_cfg.original_name, "string")
    else:
        columns = [n for n in staging_col_types if n != "geom"]
        column_types = {n: t for n, t in staging_col_types.items() if n != "geom"}

    # Fetch sample rows with transformations applied
    sample_rows: list[dict[str, object]] = []
    bbox: str | None = None
    try:
        data = read_and_transform_data(
            staging_table_name, data_engine, schema=staging_schema, config=config, limit=limit
        )
        if isinstance(data, gpd.GeoDataFrame) and not data.geometry.is_empty.all():
            bounds = data.total_bounds  # [minx, miny, maxx, maxy]
            bbox = f"BOX({bounds[0]} {bounds[1]},{bounds[2]} {bounds[3]})"
        geom_col_name: str | None = (
            data.geometry.name if isinstance(data, gpd.GeoDataFrame) else None
        )  # type: ignore[assignment]
        sample_rows = [
            {str(k): v for k, v in row.items() if str(k) != geom_col_name}
            for row in data.to_dict(orient="records")  # type: ignore[arg-type]
        ]
    except Exception as err:
        logger.warning("Could not fetch sample rows from staging %s: %s", staging_table_name, err)

    return columns, column_types, sample_rows, bbox


def _get_sample_from_final(
    integrity_link: IntegrityLink,
    limit: int = 5,
) -> tuple[list[str], dict[str, str], list[dict[str, object]], str | None]:
    """Fetch column info and sample rows from the final table (already transformed).

    Returns:
        Tuple of (columns, column_types, sample_rows, bbox) where:
        - columns: column names (geometry and id_datafeeder excluded)
        - column_types: mapping of column name → ISO 19110 type string
        - sample_rows: up to `limit` rows as dicts (geometry excluded)
        - bbox: bounding box string or None
    """
    final_table_name = integrity_link.final_table_name
    if not final_table_name:
        return [], {}, [], None

    final_schema = get_data_schema(integrity_link.integrity_organization)

    _EXCLUDED = {"geom", "id_datafeeder"}

    # Get final table column types from DB schema
    col_types: dict[str, str] = {}
    try:
        inspector = sa_inspect(data_engine)
        raw_cols = inspector.get_columns(final_table_name, schema=final_schema)
        col_types = {col["name"]: pg_type_to_iso19110(str(col["type"])) for col in raw_cols}
    except Exception as err:
        logger.warning("Could not inspect final table %s: %s", final_table_name, err)

    columns = [n for n in col_types if n not in _EXCLUDED]
    column_types = {n: t for n, t in col_types.items() if n not in _EXCLUDED}

    # Fetch sample rows (no transformation — final table is already processed)
    sample_rows: list[dict[str, object]] = []
    bbox: str | None = None
    try:
        data = read_and_transform_data(
            final_table_name, data_engine, schema=final_schema, config=None, limit=limit
        )
        if isinstance(data, gpd.GeoDataFrame) and not data.geometry.is_empty.all():
            bounds = data.total_bounds  # [minx, miny, maxx, maxy]
            bbox = f"BOX({bounds[0]} {bounds[1]},{bounds[2]} {bounds[3]})"
        geom_col_name: str | None = (
            data.geometry.name if isinstance(data, gpd.GeoDataFrame) else None
        )  # type: ignore[assignment]
        sample_rows = [
            {
                str(k): v
                for k, v in row.items()
                if str(k) != geom_col_name and str(k) not in _EXCLUDED
            }
            for row in data.to_dict(orient="records")  # type: ignore[arg-type]
        ]
    except Exception as err:
        logger.warning("Could not fetch sample rows from final table %s: %s", final_table_name, err)

    return columns, column_types, sample_rows, bbox


def generate_metadata_suggestions(
    integrity_link: IntegrityLink,
    settings: Settings,
    data_source: Literal["staging", "final"] = "staging",
    mode: LlmMetadataMode = "regenerate",
    current_values: dict[str, Any] | None = None,
    extra_context: str | None = None,
) -> GeneratedMetadata:
    """Generate AI metadata suggestions for an integrity link.

    Args:
        integrity_link: IntegrityLink record with staging/final data
        settings: Application settings
        data_source: Which table to use for analysis ("staging" or "final")

    Returns:
        GeneratedMetadata with suggested title, abstract, keywords, etc.

    Raises:
        ValueError: If AI is disabled or the requested table is not available
        Exception: On LLM or data fetching errors
    """
    if not settings.AI_ENABLED:
        raise ValueError("AI metadata generation is disabled")

    system_prompt_path = (
        Path(settings.AI_METADATA_SYSTEM_PROMPT_FILE)
        if settings.AI_METADATA_SYSTEM_PROMPT_FILE
        else None
    )
    human_prompt_path = (
        Path(settings.AI_METADATA_HUMAN_PROMPT_FILE)
        if settings.AI_METADATA_HUMAN_PROMPT_FILE
        else None
    )

    if data_source == "staging":
        if not integrity_link.staging_table_name:
            raise ValueError(f"IntegrityLink {integrity_link.id} has no staging_table_name")
        # Check if the staging table still physically exists (may have been cleaned up by Airflow)
        staging_schema = get_staging_schema()
        inspector = sa_inspect(data_engine)
        staging_exists = inspector.has_table(
            integrity_link.staging_table_name, schema=staging_schema
        )
        # Fallback: if the staging table is gone, try to use the final table instead
        if not staging_exists:
            data_source = "final"
    if data_source == "final":
        if not integrity_link.final_table_name:
            raise ValueError(
                f"IntegrityLink {integrity_link.id} has no final_table_name "
                "(staging table was deleted and no final table available)"
            )
    table_name_for_llm: str = (
        integrity_link.staging_table_name
        if data_source == "staging"
        else integrity_link.final_table_name
    )  # type: ignore[assignment]  # validated non-None above

    try:
        llm = get_llm(
            provider=settings.AI_PROVIDER,
            model=settings.AI_MODEL or None,
            api_key=settings.AI_API_KEY or "",
            base_url=settings.AI_BASE_URL or None,
            temperature=settings.AI_METADATA_TEMPERATURE,
            think=False,
        )
    except Exception:
        logger.error("Failed to initialize LLM")
        raise

    try:
        limit = settings.AI_METADATA_SAMPLE_LIMIT
        if data_source == "staging":
            columns, column_types, sample_rows, bbox = _get_sample_from_staging(
                integrity_link, limit=limit
            )
        else:
            columns, column_types, sample_rows, bbox = _get_sample_from_final(
                integrity_link, limit=limit
            )
    except Exception as e:
        logger.error(f"Failed to fetch sample from {data_source} table: {e}", exc_info=True)
        raise

    try:
        # Build priority keywords: all GeoNetwork thesauruses
        priority_kw = _fetch_keywords_from_geonetwork(
            gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
            credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
            verify_tls=settings.GEONETWORK_VERIFY_TLS,
        )
    except Exception as e:
        logger.warning(f"Failed to fetch keywords from GeoNetwork: {e}", exc_info=True)
        priority_kw = []

    try:
        # Build priority topic categories: GeoNetwork codelist, fallback to ISO 19115 list
        topics = _fetch_topic_categories_from_geonetwork(
            gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
            credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
            verify_tls=settings.GEONETWORK_VERIFY_TLS,
        )
    except Exception as e:
        logger.warning(f"Failed to fetch topic categories from GeoNetwork: {e}", exc_info=True)
        topics = []

    try:
        result = generate_metadata(
            table_name=table_name_for_llm,
            column_names=columns,
            column_types=column_types,
            llm=llm,
            title=integrity_link.integrity_title,
            extra_context=extra_context or None,
            sample_rows=sample_rows or None,
            bbox=bbox,
            keywords=priority_kw or None,
            priority_topic_categories=topics or None,
            system_prompt_path=system_prompt_path,
            human_prompt_path=human_prompt_path,
            mode=mode,
            current_values=current_values if mode == "rewrite" else None,
        )

        return result
    except Exception as e:
        logger.error(f"LLM metadata generation failed: {e}", exc_info=True)
        raise


def generate_ai_metadata(
    integrity_link: IntegrityLink,
    settings: Settings,
    data_source: Literal["staging", "final"] = "staging",
) -> None:
    """Generate AI metadata for an integrity link and update GeoNetwork.

    Soft failure: logs a warning on error, never raises.
    No-op if AI_ENABLED=False or if the integrity link has no metadata_id.

    Args:
        integrity_link: IntegrityLink record
        settings: Application settings
        data_source: Which table to use for analysis (\"staging\" or \"final\")
    """
    if not settings.AI_ENABLED:
        logger.info("AI metadata generation is disabled (AI_ENABLED=False) — skipping")
        return

    if not integrity_link.metadata_id:
        logger.info(
            f"IntegrityLink {integrity_link.id} has no metadata_id yet — skipping AI generation"
        )
        return

    if data_source == "final":
        if not integrity_link.final_table_name:
            logger.warning(
                f"IntegrityLink {integrity_link.id} has no final_table_name — skipping AI generation"
            )
            return
    else:
        if not integrity_link.staging_table_name:
            logger.warning(
                f"IntegrityLink {integrity_link.id} has no staging_table_name — skipping AI generation"
            )
            return

    try:
        # Generate metadata suggestions
        result = generate_metadata_suggestions(integrity_link, settings, data_source=data_source)

        metadata_service = MetadataService(
            gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
            datadir_path=settings.DATADIR_PATH,
            credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
            verify_tls=settings.GEONETWORK_VERIFY_TLS,
        )
        metadata_service.update_metadata(
            metadata_uuid=str(integrity_link.metadata_id),
            title=result.title,
            abstract=result.abstract,
            keywords=result.keywords,
            topic_categories=result.topic_categories,
            attribute_descriptions=result.attribute_descriptions,
            temporal_extent=result.temporal_extent,
            table_name=integrity_link.final_table_name or "",
            generate_by_ai=True,
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
