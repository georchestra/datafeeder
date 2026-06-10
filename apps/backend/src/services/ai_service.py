"""Service for AI-based metadata generation."""

from pathlib import Path

import requests
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


def _fetch_thesaurus_keywords(
    gn_api_url: str,
    thesaurus_ids: list[str],
    credentials: tuple[str, str],
    max_results: int = 200,
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
                verify=False,
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
            timeout=10,
            verify=False,
        )
        resp.raise_for_status()
        thesaurus_ids = [t["key"] for t in resp.json() if "key" in t]
        logger.info("Found %d thesauruses in GeoNetwork", len(thesaurus_ids))
    except Exception as err:
        logger.warning("Could not list GeoNetwork thesauruses: %s", err)
        return []

    # Step 2: fetch keywords for each thesaurus
    return _fetch_thesaurus_keywords(gn_api_url, thesaurus_ids, credentials, max_results)


def _fetch_topic_categories_from_geonetwork(
    gn_api_url: str,
    credentials: tuple[str, str],
) -> list[str]:
    """Fetch ISO 19115 MD_TopicCategoryCode values from GeoNetwork's registries API.

    Uses: GET /api/registries/entries?registry={codelist_url}&lang=fre
    Falls back to an empty list (LLM uses the full ISO list from the system prompt) on error.

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
            params={"registry": registry_url, "lang": "fre", "rows": 50},
            timeout=10,
            verify=False,
        )
        resp.raise_for_status()
        data = resp.json()
        # Each entry has a "value" (the code) and optional "label"
        categories = [item["value"] for item in data if "value" in item]
        if categories:
            logger.info("Fetched %d topic categories from GeoNetwork", len(categories))
            return categories
    except Exception as err:
        logger.warning("Could not fetch topic categories from GeoNetwork: %s", err)
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
        raw_cols = inspector.get_columns(final_table_name, schema=target_schema)
        columns: list[str] = [col["name"] for col in raw_cols]
        column_types: dict[str, str] = {col["name"]: str(col["type"]) for col in raw_cols}

        # Fetch 5 sample rows and bbox from the final table
        sample_rows, bbox = _get_sample_rows(final_table_name, target_schema)

        # Build priority keywords: all GeoNetwork thesauruses
        priority_kw = _fetch_keywords_from_geonetwork(
            gn_api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
            credentials=(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
        )

        # Build priority topic categories: GeoNetwork codelist
        gn_api_url = f"{settings.GEONETWORK_INTERNAL_URL}/srv/api"
        gn_credentials = (settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD)
        priority_topics = _fetch_topic_categories_from_geonetwork(gn_api_url, gn_credentials)

        result = generate_metadata(
            table_name=final_table_name,
            column_names=columns,
            column_types=column_types,
            llm=llm,
            title=integrity_link.integrity_title,
            sample_rows=sample_rows or None,
            bbox=bbox,
            priority_keywords=priority_kw or None,
            priority_topic_categories=priority_topics or None,
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
            attribute_descriptions=result.attribute_descriptions,
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
