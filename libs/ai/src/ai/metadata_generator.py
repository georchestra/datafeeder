"""AI-powered metadata generation using LangChain."""

import logging
from pathlib import Path
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ai.metadata_generator_models import GeneratedMetadata, LlmMetadataMode
from ai.utils import load_prompt

logger = logging.getLogger(__name__)
_MAX_PROMPT_KEYWORDS = 100


def format_sample(sample_rows: list[Any] | None) -> str:
    """Format sample rows as a compact CSV-like string for the prompt (values only, no headers)."""
    if not sample_rows:
        return "not available"
    headers = list(sample_rows[0].keys())
    lines = [", ".join(str(row.get(h, "")) for h in headers) for row in sample_rows]
    return "\n".join(lines)


def format_column_headers(
    column_names: list[str], column_types: dict[str, str] | None = None
) -> str:
    """Format column names with their types as a comma-separated string.

    Args:
        column_names: List of column names
        column_types: Optional mapping of column name → SQL type string

    Returns:
        Formatted string like "col1 (type1), col2, col3 (type3)"
    """
    return ", ".join(
        f"{n} ({column_types[n]})" if column_types and n in column_types else n
        for n in column_names
    )


def format_keywords_for_prompt(keywords: list[str] | None) -> str:
    """Deduplicate and cap keywords before injecting them into the LLM prompt."""
    if not keywords:
        return ""

    # Keep order, drop empty values, and hard-cap size to avoid prompt bloat.
    seen: set[str] = set()
    cleaned = [k.strip() for k in keywords if k.strip()]
    deduped = [k for k in cleaned if not (k in seen or seen.add(k))]
    return ", ".join(deduped[:_MAX_PROMPT_KEYWORDS])


def format_title_for_prompt(
    table_name: str,
    title: str | None,
    current_values: dict[str, Any] | None,
) -> str:
    """Resolve title value sent to the prompt."""
    return (current_values.get("title") if current_values else None) or title or table_name


def format_bbox_for_prompt(bbox: str | None) -> str:
    """Normalize bbox value for prompt injection."""
    return bbox or "not available"


def format_current_abstract_for_prompt(current_values: dict[str, Any] | None) -> str:
    """Format current abstract value for rewrite mode context."""
    if current_values and current_values.get("abstract"):
        return f"{current_values['abstract']}"
    return ""


def format_current_keywords_for_prompt(current_values: dict[str, Any] | None) -> str:
    """Format current keywords value for rewrite mode context."""
    if current_values and current_values.get("keywords"):
        return f"{current_values['keywords']}"
    return ""


def format_current_topics_for_prompt(current_values: dict[str, Any] | None) -> str:
    """Format current topics value for rewrite mode context."""
    if current_values and current_values.get("topics"):
        return f"{current_values['topics']}"
    return ""


def format_topics_for_prompt(priority_topic_categories: list[str] | None) -> str:
    """Format preferred topic categories for prompt injection."""
    return ", ".join(priority_topic_categories) if priority_topic_categories else ""


def format_extra_context_for_prompt(
    extra_context: str | dict[str, Any] | None,
) -> str | dict[str, Any]:
    """Format extra context payload for prompt injection."""
    return extra_context if extra_context else ""


def generate_metadata(
    table_name: str,
    column_names: list[str],
    llm: BaseChatModel,
    column_types: dict[str, str] | None = None,
    title: str | None = None,
    extra_context: str | dict[str, Any] | None = None,
    sample_rows: list[dict[str, object]] | None = None,
    bbox: str | None = None,
    keywords: list[str] | None = None,
    priority_topic_categories: list[str] | None = None,
    system_prompt_path: Path | str | None = None,
    human_prompt_path: Path | str | None = None,
    mode: LlmMetadataMode = "regenerate",
    current_values: dict[str, Any] | None = None,
) -> GeneratedMetadata:
    """Generate dataset metadata using an LLM.

    All configuration (LLM instance, prompt paths) must be passed explicitly.

    Args:
        table_name: Name of the final PostGIS table
        column_names: List of column names in the table
        llm: LangChain chat model instance to use
        column_types: Mapping of column name → SQL type string (optional)
        title: Human-readable title already chosen by the user (optional)
        extra_context: Additional context as string or dict to pass to the prompt (optional)
        sample_rows: Up to 5 sample rows from the table for richer inference (optional)
        bbox: Bounding box string "minx, miny, maxx, maxy" for geographic context (optional)
        keywords: Preferred keywords to use when relevant (optional)
        priority_topic_categories: Preferred ISO 19115 topic categories to favour (optional)
        system_prompt_path: Path to a custom system prompt file (optional)
        human_prompt_path: Path to a custom human prompt file (optional)

    Returns:
        GeneratedMetadata with title, abstract, keywords and topic_categories
    """
    parser = PydanticOutputParser(pydantic_object=GeneratedMetadata)

    system_prompt = load_prompt(system_prompt_path, default="metadata_system.md")
    human_prompt = load_prompt(human_prompt_path, default="metadata_human.md")

    prompt = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", human_prompt)]
    ).partial(format_instructions=parser.get_format_instructions())

    chain = prompt | llm | parser

    result = chain.invoke(
        {
            "title": format_title_for_prompt(table_name, title, current_values),
            "columns_with_types": format_column_headers(column_names, column_types),
            "sample": format_sample(sample_rows),
            "bbox": format_bbox_for_prompt(bbox),
            "current_abstract": format_current_abstract_for_prompt(current_values),
            "current_keywords": format_current_keywords_for_prompt(current_values),
            "current_topics": format_current_topics_for_prompt(current_values),
            "keywords": format_keywords_for_prompt(keywords),
            "topics": format_topics_for_prompt(priority_topic_categories),
            "extra_context": format_extra_context_for_prompt(extra_context),
            "mode_instruction": (
                "REWRITE — improve, rephrase and enrich the existing values if provided above. "
                "Keep the meaning but make them clearer, more professional and more complete."
                if mode == "rewrite"
                else "REGENERATE — For title only, minor rewording allowed to integrate current_abstract location if provided. Other fields: no reformulation."
            ),
        }
    )

    return result
