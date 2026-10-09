"""Service for AI-based metadata generation."""

from pathlib import Path
from typing import Any

from ai.metadata_generator import MAX_KEYWORDS_PER_THESAURUS, generate_metadata
from ai.metadata_generator_models import (
    GeneratedMetadata,
    LlmMetadataDataSource,
    LlmMetadataMode,
    Thesaurus,
)
from ai.providers import get_llm
from ai.utils import pg_type_to_iso19110  # type: ignore[import-untyped]
from data_manipulation import (
    IntegrityTransformation,
    build_transformation_select,
    read_transformed_preview,
)
from data_manipulation.constants import DEFAULT_GEOMETRY_COLUMN
from data_manipulation.transformation.sql_transform import ensure_cast_helpers
from geonetwork import GnApi  # type: ignore[import-untyped]
from geonetwork.gn_session import Credentials  # type: ignore[import-untyped]
from sqlalchemy import MetaData, Table, func, select
from sqlalchemy import inspect as sa_inspect

from src.core.config import Settings, get_data_schema, get_staging_schema
from src.core.db import data_engine
from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.services.metadata_service import MetadataService

logger = get_logger()

# Fallback ISO 19115 topic categories, using the keys of the GeoNetwork UI
_FALLBACK_TOPIC_CATEGORIES = [
    "biota",
    "boundaries",
    "climatologyMeteorologyAtmosphere",
    "economy",
    "elevation",
    "environment",
    "farming",
    "geoscientific information",
    "health",
    "imageryBaseMapsEarthCover",
    "inlandWaters",
    "intelligenceMilitary",
    "Location",
    "Oceans",
    "planningCadastre",
    "Society",
    "Structure",
    "Transportation",
    "utilitiesCommunication",
]


def _fetch_thesaurus_keywords(
    gn_api: GnApi,
    thesaurus_id: str,
    max_results: int = 200,
) -> list[tuple[str, str]]:
    """Fetch keyword ids and labels from one GeoNetwork thesaurus.

    Uses the GeoNetwork REST API: GET /registries/vocabularies/search

    Args:
        gn_api: GeoNetwork API wrapper (github.com/camptocamp/python-geonetwork)
        thesaurus_id: thesaurus identifiers (e.g. "external.theme.inspire-theme")
        max_results: Maximum number of keywords to fetch per thesaurus

    Returns:
        Deduplicated (uri, label) tuple for each keyword.

    Raises:
        Exception: if the thesaurus cannot be fetched
    """
    try:
        resp = gn_api.session.get(
            f"{gn_api.api_url}/registries/vocabularies/search",
            # A single lang only: GeoNetwork fails to parse "fre,eng"
            params={"lang": "fre", "rows": max_results, "thesaurus": thesaurus_id},
        )
        resp.raise_for_status()
        data: list[dict[str, Any]] = resp.json()
    except Exception as err:
        logger.warning("Could not fetch thesaurus %s from GeoNetwork: %s", thesaurus_id, err)
        raise
    # Deduplicate by uri while preserving order, drop keywords without uri or label
    keywords: dict[str, str] = {}
    for item in data:
        uri, label = item.get("uri"), item.get("value")
        if uri and label and uri not in keywords:
            keywords[uri] = label
    return list(keywords.items())


def _fetch_thesaurus_from_geonetwork(gn_api: GnApi) -> dict[str, str]:
    """Fetch thesaurus ids and titles from GeoNetwork.

    Auto-discovers all available thesauruses via GET /thesaurus

    Args:
        gn_api: GeoNetwork API wrapper (github.com/camptocamp/python-geonetwork)

    Returns:
        Mapping of thesaurus id to thesaurus title
    """
    thesaurus_titles: dict[str, str] = {}
    try:
        resp = gn_api.session.get(
            f"{gn_api.api_url}/thesaurus",
            params={"_content_type": "json"},
        )
        resp.raise_for_status()
        data = resp.json()
        # GeoNetwork wraps the thesaurus list in an extra array: [[{...}, ...]]
        if data and isinstance(data[0], list):
            data = data[0]
        thesaurus_titles = {t["key"]: t.get("title") or t["key"] for t in data if "key" in t}
        logger.info("Found %d thesauruses in GeoNetwork", len(thesaurus_titles))
    except Exception as err:
        logger.warning("Could not list GeoNetwork thesauruses: %s", err)
    return thesaurus_titles


def _fetch_keywords_from_geonetwork(
    gn_api: GnApi,
    allowed_thesaurus: list[str],
) -> dict[str, Thesaurus]:
    """Fetch the keywords of the allowed GeoNetwork thesauruses, grouped by thesaurus.

    Args:
        gn_api: GeoNetwork API wrapper (github.com/camptocamp/python-geonetwork)
        allowed_thesaurus: Whitelist of thesaurus ids to use

    Returns:
        Mapping of thesaurus id to its title and (uri, label) keywords.
        Thesauruses that are unavailable or empty are skipped.
    """
    thesaurus_titles = _fetch_thesaurus_from_geonetwork(gn_api)
    missing = [t for t in allowed_thesaurus if t not in thesaurus_titles]
    if missing:
        logger.warning("Allowed thesauruses not found in GeoNetwork: %s", ", ".join(missing))

    all_kw: dict[str, Thesaurus] = {}
    for thesaurus_id in allowed_thesaurus:
        if thesaurus_id not in thesaurus_titles:
            continue
        try:
            kw = _fetch_thesaurus_keywords(
                gn_api, thesaurus_id, max_results=MAX_KEYWORDS_PER_THESAURUS
            )
        except Exception:
            continue
        if kw:
            all_kw[thesaurus_id] = {"title": thesaurus_titles[thesaurus_id], "kw": kw}
    return all_kw


def _fetch_topic_categories_from_geonetwork(gn_api: GnApi) -> list[str]:
    """Fetch ISO 19115 MD_TopicCategoryCode values from GeoNetwork's standards API.

    Uses: GET /standards/iso19139/codelists/gmd:MD_TopicCategoryCode
    Falls back on a constant list if the endpoint is unavailable.

    Args:
        gn_api: GeoNetwork API wrapper (github.com/camptocamp/python-geonetwork)

    Returns:
        List of ISO 19115 topic category code strings.
    """
    try:
        resp = gn_api.session.get(
            f"{gn_api.api_url}/standards/iso19139/codelists/gmd:MD_TopicCategoryCode"
        )
        resp.raise_for_status()
        # Response maps each code to its label: {"farming": "Farming", ...}
        categories = list(resp.json())
        if categories:
            logger.info("Fetched %d topic categories from GeoNetwork", len(categories))
            return categories
    except Exception as err:
        logger.warning("Could not fetch topic categories from GeoNetwork: %s", err)
    logger.warning("Falling back on constant topic categories list")
    return list(_FALLBACK_TOPIC_CATEGORIES)


def _compute_bbox(
    table_name: str,
    schema: str,
    config: IntegrityTransformation | None,
) -> str | None:
    """Compute the extent of the transformed table geometry in the database.

    Returns:
        PostGIS ``ST_Extent`` string (``BOX(minx miny,maxx maxy)``) in the
        table's native SRID, or None if the table has no (non-empty) geometry.
    """
    table = Table(table_name, MetaData(schema=schema), autoload_with=data_engine)
    tq = build_transformation_select(table, config)
    if tq.geom_column is None:
        return None
    core = tq.select.subquery()
    with data_engine.connect() as conn:
        ensure_cast_helpers(conn)
        return conn.execute(select(func.ST_Extent(core.c[tq.geom_column]))).scalar()


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
        preview = read_transformed_preview(
            staging_table_name, data_engine, config, schema=staging_schema, limit=limit
        )
        sample_rows = [
            {k: v for k, v in row.items() if k != DEFAULT_GEOMETRY_COLUMN} for row in preview.rows
        ]
        if preview.is_geographic:
            bbox = _compute_bbox(staging_table_name, staging_schema, config)
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
        preview = read_transformed_preview(
            final_table_name, data_engine, None, schema=final_schema, limit=limit
        )
        sample_rows = [{k: v for k, v in row.items() if k not in _EXCLUDED} for row in preview.rows]
        if preview.is_geographic:
            bbox = _compute_bbox(final_table_name, final_schema, None)
    except Exception as err:
        logger.warning("Could not fetch sample rows from final table %s: %s", final_table_name, err)

    return columns, column_types, sample_rows, bbox


def get_metadata_suggestions(
    integrity_link: IntegrityLink,
    settings: Settings,
    data_source: LlmMetadataDataSource = LlmMetadataDataSource.STAGING,
    mode: LlmMetadataMode = LlmMetadataMode.REGENERATE,
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

    if data_source == LlmMetadataDataSource.STAGING:
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
            data_source = LlmMetadataDataSource.FINAL
    if data_source == LlmMetadataDataSource.FINAL:
        if not integrity_link.final_table_name:
            raise ValueError(
                f"IntegrityLink {integrity_link.id} has no final_table_name "
                "(staging table was deleted and no final table available)"
            )
    table_name_for_llm: str = (
        integrity_link.staging_table_name
        if data_source == LlmMetadataDataSource.STAGING
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
        if data_source == LlmMetadataDataSource.STAGING:
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
        gn_api = GnApi(
            api_url=f"{settings.GEONETWORK_INTERNAL_URL}/srv/api",
            credentials=Credentials(settings.GEONETWORK_USERNAME, settings.GEONETWORK_PASSWORD),
            verifytls=settings.GEONETWORK_VERIFY_TLS,
        )
    except Exception as e:
        logger.warning(f"Could not connect to GeoNetwork: {e}", exc_info=True)
        gn_api = None

    all_kw: dict[str, Thesaurus] = {}
    topics = list(_FALLBACK_TOPIC_CATEGORIES)
    if gn_api is not None:
        # Build keywords as a tree: whitelisted thesauri and then all keywords per thesaurus
        allowed_thesaurus = [
            t.strip() for t in settings.AI_ALLOWED_THESAURUS.split(",") if t.strip()
        ]
        all_kw = _fetch_keywords_from_geonetwork(gn_api, allowed_thesaurus)
        topics = _fetch_topic_categories_from_geonetwork(gn_api)

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
            keywords=all_kw,
            topic_categories=topics,
            system_prompt_path=system_prompt_path,
            human_prompt_path=human_prompt_path,
            mode=mode,
            current_values=current_values if mode == LlmMetadataMode.REWRITE else None,
        )

        return result
    except Exception as e:
        logger.error(f"LLM metadata generation failed: {e}", exc_info=True)
        raise


def generate_ai_metadata(
    integrity_link: IntegrityLink,
    settings: Settings,
    data_source: LlmMetadataDataSource = LlmMetadataDataSource.STAGING,
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

    if data_source == LlmMetadataDataSource.FINAL:
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
        result = get_metadata_suggestions(integrity_link, settings, data_source=data_source)

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
