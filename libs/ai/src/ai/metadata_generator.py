"""AI-powered metadata generation using LangChain."""

import json
import logging
from pathlib import Path
from typing import Any
from enum import StrEnum

from pydantic import create_model
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate

from ai.metadata_generator_models import GeneratedMetadata, LlmMetadataMode, Thesaurus, KwStrategy
from ai.utils import load_prompt

logger = logging.getLogger(__name__)
_MAX_KEYWORDS_PER_THESAURUS = 1024
_MAX_PROMPT_KEYWORDS = 1024
_MAX_PROMPT_TITLE_CHARS = 256
_MAX_PROMPT_ABSTRACT_CHARS = 2048
_MAX_PROMPT_KEYWORDS_CHARS = 16384
_MAX_PROMPT_TOPICS_CHARS = 512
_MAX_PROMPT_EXTRA_CONTEXT_CHARS = 1024


def _truncate_text(value: str, max_chars: int) -> str:
    """Truncate text to a maximum number of characters."""
    return value[:max_chars]


def _stringify_prompt_value(value: Any) -> str:
    """Normalize prompt values to string form."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


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
    cleaned = [kw.strip() for v in keywords.values() for k, kw in v['kw'] if kw.strip()]
    deduped = [k for k in cleaned if not (k in seen or seen.add(k))]
    logger.info(f"Count KW: {len(deduped)} (of total {len(cleaned)})", exc_info=True)
    return _truncate_text(
        ", ".join(deduped[:_MAX_PROMPT_KEYWORDS]),
        _MAX_PROMPT_KEYWORDS_CHARS,
    )


def format_title_for_prompt(
    table_name: str,
    title: str | None,
    current_values: dict[str, Any] | None,
) -> str:
    """Resolve title value sent to the prompt."""
    resolved_title = (
        (current_values.get("title") if current_values else None) or title or table_name
    )
    return _truncate_text(_stringify_prompt_value(resolved_title), _MAX_PROMPT_TITLE_CHARS)


def format_bbox_for_prompt(bbox: str | None) -> str:
    """Normalize bbox value for prompt injection."""
    return bbox or "not available"


def format_current_abstract_for_prompt(current_values: dict[str, Any] | None) -> str:
    """Format current abstract value for rewrite mode context."""
    if current_values and current_values.get("abstract"):
        return _truncate_text(
            _stringify_prompt_value(current_values.get("abstract")),
            _MAX_PROMPT_ABSTRACT_CHARS,
        )
    return ""


def format_current_keywords_for_prompt(current_values: dict[str, Any] | None) -> str:
    """Format current keywords value for rewrite mode context."""
    if current_values and current_values.get("keywords"):
        return _truncate_text(
            _stringify_prompt_value(current_values.get("keywords")),
            _MAX_PROMPT_KEYWORDS_CHARS,
        )
    return ""


def format_current_topics_for_prompt(current_values: dict[str, Any] | None) -> str:
    """Format current topics value for rewrite mode context."""
    if current_values and current_values.get("topics"):
        return _truncate_text(
            _stringify_prompt_value(current_values.get("topics")),
            _MAX_PROMPT_TOPICS_CHARS,
        )
    return ""


def format_topics_for_prompt(topic_categories: list[str] | None) -> str:
    """Format preferred topic categories for prompt injection."""
    return ", ".join(topic_categories) if topic_categories else ""


def format_extra_context_for_prompt(
    extra_context: str | dict[str, Any] | None,
) -> str:
    """Format extra context payload for prompt injection."""
    if not extra_context:
        return ""
    if isinstance(extra_context, dict):
        serialized = json.dumps(extra_context, ensure_ascii=False)
        return _truncate_text(serialized, _MAX_PROMPT_EXTRA_CONTEXT_CHARS)
    return _truncate_text(_stringify_prompt_value(extra_context), _MAX_PROMPT_EXTRA_CONTEXT_CHARS)


def generate_metadata(
    table_name: str,
    column_names: list[str],
    llm: BaseChatModel,
    column_types: dict[str, str] | None = None,
    title: str | None = None,
    extra_context: str | dict[str, Any] | None = None,
    sample_rows: list[dict[str, object]] | None = None,
    bbox: str | None = None,
    keywords: dict[str, Thesaurus] | None = None,
    topic_categories: list[str] | None = None,
    system_prompt_path: Path | str | None = None,
    human_prompt_path: Path | str | None = None,
    mode: LlmMetadataMode = LlmMetadataMode.REGENERATE,
    current_values: dict[str, Any] | None = None,
    keyword_strategy: KwStrategy = KwStrategy.STRUCTURED
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
        keywords: Keywords to be used (optional, structured by parent thesaurus)
        topic_categories: ISO 19115 topic categories (optional)
        system_prompt_path: Path to a custom system prompt file (optional)
        human_prompt_path: Path to a custom human prompt file (optional)
        keyword_strategy: prompted, structured, staged

    Returns:
        GeneratedMetadata with title, abstract, keywords and topic_categories
    """
    system_prompt = load_prompt(system_prompt_path, default="metadata_system.md")
    human_prompt = load_prompt(human_prompt_path, default="metadata_human.md")

    prompt_template = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", human_prompt)]
    )

    if keyword_strategy == KwStrategy.PROMPTED:
        # convert pydantic model to system input prompt
        parser = PydanticOutputParser(pydantic_object=GeneratedMetadata)

        prompt = prompt_template.partial(format_instructions=parser.get_format_instructions())

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
                "kw_policy": "Choose **between 8 and 12** relevant keywords.",
                "topics": format_topics_for_prompt(topic_categories),
                "extra_context": format_extra_context_for_prompt(extra_context),
                "mode_instruction": (
                    "REWRITE — improve, rephrase and enrich the existing values if provided above. "
                    "Keep the meaning but make them clearer, more professional and more complete."
                    if mode == LlmMetadataMode.REWRITE
                    else "REGENERATE — For title only, minor rewording allowed to integrate current_abstract location if provided. Other fields: no reformulation."
                ),
            }
        )
    else:
        # using a tool for structured json output may save some tokens and is more explicit
        # authorized topics and keywords are mapped dynamically into the model

        # Fill the prompt placeholder, no structure instructions needed, these will be communicated via tool
        prompt = prompt_template.partial(format_instructions='')

        # Enum name = enum value for simplicity
        InspireCategories = StrEnum('InspireCategories', zip(topic_categories, topic_categories))

        if keyword_strategy == KwStrategy.STRUCTURED:  # oneshot KWs
            seen: set[str] = set()
            kw_tuples = [kwt for v in keywords.values() for kwt in v['kw'] if not (kwt[1] in seen or seen.add(kwt[1]))]
            logger.info(f"Count KW: {len(set(v for k, v in kw_tuples))} (of total {len(kw_tuples)})", exc_info=True)
            kw_policy = "Choose **between 5 and 12** relevant keywords."

        elif keyword_strategy == KwStrategy.STAGED:
            kw_tuples = [(k, v['title']) for k, v in keywords.items()]
            kw_policy = "Choose 1 or 2 relevant keyword categories."
        else:
            raise Exception("Shall not happen")

        # kw_tuples: (key, title)
        KWCategories = StrEnum('KWCategories', kw_tuples)

        # override Pydantic model to use custom categories (enums)
        TemplatedModel = create_model(
            'TemplatedModel',
            __base__=GeneratedMetadata,
            topic_categories=list[InspireCategories],
            keywords=list[KWCategories],
        )
        # strict option is important, otherwise the llm may hallucinate non authorized values
        chain = prompt | llm.with_structured_output(TemplatedModel, strict=True)

        result = chain.invoke(
            {
                "title": format_title_for_prompt(table_name, title, current_values),
                "columns_with_types": format_column_headers(column_names, column_types),
                "sample": format_sample(sample_rows),
                "bbox": format_bbox_for_prompt(bbox),
                "current_abstract": format_current_abstract_for_prompt(current_values),
                "current_keywords": format_current_keywords_for_prompt(current_values),
                "current_topics": format_current_topics_for_prompt(current_values),
                "keywords": "see below in tool",
                "kw_policy": kw_policy,
                "topics": "see below in tool",
                "extra_context": format_extra_context_for_prompt(extra_context),
                "mode_instruction": (
                    "REWRITE — improve, rephrase and enrich the existing values if provided above. "
                    "Keep the meaning but make them clearer, more professional and more complete."
                    if mode == LlmMetadataMode.REWRITE
                    else "REGENERATE — For title only, minor rewording allowed to integrate current_abstract location if provided. Other fields: no reformulation."
                ),
            }
        )
        if keyword_strategy == KwStrategy.STAGED:
            # second stage where KW are actually selected from a narrower choice
            kw = keywords[result.keywords[0].name]['kw']
            Keywords = StrEnum('Themes', kw)
            KeywordModel = create_model('KeywordModel', keywords=list[Keywords])

            kw_chain = llm.with_structured_output(KeywordModel, strict=True)
            kw_list = kw_chain.invoke(
                f"""
                Choose **between 5 and 12** keywords corresponding to:
                # Title:
                {result.title}

                # Abstract:
                {result.abstract}
                """
            )
            # update keywords with refined values
            result.keywords = kw_list.keywords

    return result
