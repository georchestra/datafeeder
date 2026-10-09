"""Unit tests for metadata_generator module."""

import json
from typing import Any

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda

from ai.metadata_generator import (
    _MAX_PROMPT_KEYWORDS,  # pyright: ignore[reportPrivateUsage]
    format_bbox_for_prompt,
    format_column_headers,
    format_current_abstract_for_prompt,
    format_current_keywords_for_prompt,
    format_current_topics_for_prompt,
    format_extra_context_for_prompt,
    format_keywords_for_prompt,
    format_sample,
    format_title_for_prompt,
    format_topics_for_prompt,
    generate_metadata,
)
from ai.metadata_generator_models import KwStrategy, Thesaurus


class TestFormatSample:
    """Tests for format_sample."""

    def test_empty_sample(self) -> None:
        """Test with None or empty list."""
        assert format_sample(None) == "not available"
        assert format_sample([]) == "not available"

    def test_single_row(self) -> None:
        """Test with single row."""
        sample = [{"name": "Alice", "age": 30}]
        result = format_sample(sample)
        assert "Alice" in result
        assert "30" in result

    def test_multiple_rows(self) -> None:
        """Test with multiple rows."""
        sample = [
            {"id": 1, "status": "active"},
            {"id": 2, "status": "inactive"},
        ]
        result = format_sample(sample)
        assert "1" in result
        assert "2" in result
        assert "active" in result
        assert "inactive" in result


class TestFormatColumnHeaders:
    """Tests for format_column_headers."""

    def test_no_types(self) -> None:
        """Test without column types."""
        columns = ["id", "name", "email"]
        result = format_column_headers(columns)
        assert result == "id, name, email"

    def test_with_types(self) -> None:
        """Test with column types."""
        columns = ["id", "name", "created"]
        types = {"id": "integer", "name": "string", "created": "date"}
        result = format_column_headers(columns, types)
        assert "id (integer)" in result
        assert "name (string)" in result
        assert "created (date)" in result

    def test_partial_types(self) -> None:
        """Test with partial column types."""
        columns = ["id", "name"]
        types = {"id": "integer"}
        result = format_column_headers(columns, types)
        assert "id (integer)" in result
        assert "name" in result
        assert result.count("(") == 1


def _thesaurus(*labels: str, title: str = "Thesaurus") -> dict[str, Thesaurus]:
    """Build a single-thesaurus keywords mapping from labels."""
    return {title: {"title": title, "kw": [(f"uri/{i}", label) for i, label in enumerate(labels)]}}


class TestFormatKeywordsForPrompt:
    """Tests for format_keywords_for_prompt."""

    def test_none_keywords(self) -> None:
        """Test with None."""
        assert format_keywords_for_prompt(None) == ""

    def test_empty_keywords(self) -> None:
        """Test with empty mapping."""
        assert format_keywords_for_prompt({}) == ""

    def test_single_keyword(self) -> None:
        """Test with single keyword."""
        assert format_keywords_for_prompt(_thesaurus("water")) == "water"

    def test_multiple_keywords(self) -> None:
        """Test with multiple keywords."""
        result = format_keywords_for_prompt(_thesaurus("water", "river", "flood"))
        assert "water" in result
        assert "river" in result
        assert "flood" in result

    def test_multiple_thesauri(self) -> None:
        """Test that keywords of every thesaurus are included."""
        result = format_keywords_for_prompt(
            {**_thesaurus("water"), **_thesaurus("forest", title="Other")}
        )
        assert "water" in result
        assert "forest" in result

    def test_deduplication(self) -> None:
        """Test deduplication of keywords."""
        result = format_keywords_for_prompt(_thesaurus("water", "water", "river", "river"))
        assert result.count("water") == 1
        assert result.count("river") == 1

    def test_whitespace_trimming(self) -> None:
        """Test trimming of whitespace."""
        result = format_keywords_for_prompt(_thesaurus("  water  ", " river ", "flood"))
        assert "  " not in result
        assert "water" in result
        assert "river" in result

    def test_max_keywords_cap(self) -> None:
        """Test that keywords are capped at _MAX_PROMPT_KEYWORDS."""
        keywords = _thesaurus(*(f"kw{i}" for i in range(_MAX_PROMPT_KEYWORDS + 50)))
        result = format_keywords_for_prompt(keywords)
        # Count commas + 1 to get number of keywords
        keyword_count = result.count(", ") + 1 if result else 0
        assert keyword_count <= _MAX_PROMPT_KEYWORDS


class TestFormatTitleForPrompt:
    """Tests for format_title_for_prompt."""

    def test_title_only(self) -> None:
        """Test with title provided."""
        result = format_title_for_prompt("table", "My Title", None)
        assert result == "My Title"

    def test_fallback_to_table_name(self) -> None:
        """Test fallback to table name."""
        result = format_title_for_prompt("my_table", None, None)
        assert result == "my_table"

    def test_current_values_priority(self) -> None:
        """Test that current_values takes priority."""
        current = {"title": "Current Title"}
        result = format_title_for_prompt("table", "New Title", current)
        assert result == "Current Title"


class TestFormatBboxForPrompt:
    """Tests for format_bbox_for_prompt."""

    def test_with_bbox(self) -> None:
        """Test with bbox provided."""
        bbox = "BOX(0 0, 10 10)"
        assert format_bbox_for_prompt(bbox) == bbox

    def test_without_bbox(self) -> None:
        """Test without bbox."""
        assert format_bbox_for_prompt(None) == "not available"


class TestFormatCurrentAbstractForPrompt:
    """Tests for format_current_abstract_for_prompt."""

    def test_with_abstract(self) -> None:
        """Test with abstract in current_values."""
        current = {"abstract": "This is a dataset"}
        result = format_current_abstract_for_prompt(current)
        assert result == "This is a dataset"

    def test_without_abstract(self) -> None:
        """Test without abstract."""
        assert format_current_abstract_for_prompt(None) == ""
        assert format_current_abstract_for_prompt({}) == ""


class TestFormatCurrentKeywordsForPrompt:
    """Tests for format_current_keywords_for_prompt."""

    def test_with_keywords(self) -> None:
        """Test with keywords in current_values."""
        current = {"keywords": "water, river, flood"}
        result = format_current_keywords_for_prompt(current)
        assert result == "water, river, flood"

    def test_without_keywords(self) -> None:
        """Test without keywords."""
        assert format_current_keywords_for_prompt(None) == ""
        assert format_current_keywords_for_prompt({}) == ""


class TestFormatCurrentTopicsForPrompt:
    """Tests for format_current_topics_for_prompt."""

    def test_with_topics(self) -> None:
        """Test with topics in current_values."""
        current = {"topics": "environment, hydrology"}
        result = format_current_topics_for_prompt(current)
        assert result == "environment, hydrology"

    def test_without_topics(self) -> None:
        """Test without topics."""
        assert format_current_topics_for_prompt(None) == ""
        assert format_current_topics_for_prompt({}) == ""


class TestFormatTopicsForPrompt:
    """Tests for format_topics_for_prompt."""

    def test_with_topics(self) -> None:
        """Test with topics list."""
        topics = ["environment", "hydrology"]
        result = format_topics_for_prompt(topics)
        assert "environment" in result
        assert "hydrology" in result

    def test_without_topics(self) -> None:
        """Test without topics."""
        assert format_topics_for_prompt(None) == ""
        assert format_topics_for_prompt([]) == ""


class TestFormatExtraContextForPrompt:
    """Tests for format_extra_context_for_prompt."""

    def test_with_string_context(self) -> None:
        """Test with string context."""
        context = "Additional information"
        result = format_extra_context_for_prompt(context)
        assert result == context

    def test_with_dict_context(self) -> None:
        """Test with dict context."""
        context = {"key": "value"}
        result = format_extra_context_for_prompt(context)
        assert result == context

    def test_without_context(self) -> None:
        """Test without context."""
        assert format_extra_context_for_prompt(None) == ""


class TestGenerateMetadata:
    """Tests for generate_metadata."""

    def test_falls_back_to_prompted_without_keywords(self) -> None:
        """Without keywords nor topic categories (e.g. GeoNetwork unavailable), the structured
        strategies cannot build their enums: generation must fall back to the prompted strategy."""
        llm = FakeListChatModel(
            responses=[
                json.dumps(
                    {
                        "title": "Rivers",
                        "abstract": "Rivers of the area.",
                        "keywords": ["water"],
                        "topic_categories": ["inlandWaters"],
                    }
                )
            ]
        )
        result = generate_metadata(
            table_name="rivers",
            column_names=["name"],
            llm=llm,
            keywords=None,
            topic_categories=None,
            keyword_strategy=KwStrategy.STAGED,
        )
        assert result.title == "Rivers"
        assert result.keywords == ["water"]

    def test_falls_back_to_prompted_without_structured_output(self) -> None:
        """When the LLM answers with plain text instead of calling the output tool,
        LangChain parses None: generation must fall back to the prompted strategy."""

        class NoToolCallChatModel(FakeListChatModel):
            def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
                return RunnableLambda(
                    lambda _: {"raw": "plain text", "parsed": None, "parsing_error": None}
                )

        llm = NoToolCallChatModel(
            responses=[
                json.dumps(
                    {
                        "title": "Rivers",
                        "abstract": "Rivers of the area.",
                        "keywords": ["water"],
                        "topic_categories": ["inlandWaters"],
                    }
                )
            ]
        )
        result = generate_metadata(
            table_name="rivers",
            column_names=["name"],
            llm=llm,
            keywords=_thesaurus("water"),
            topic_categories=["inlandWaters"],
            keyword_strategy=KwStrategy.STAGED,
        )
        assert result.title == "Rivers"
        assert result.keywords == ["water"]
