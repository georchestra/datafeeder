"""Unit tests for metadata_generator module."""

from ai.metadata_generator import (
    _format_bbox_for_prompt,
    _format_column_headers,
    _format_current_abstract_for_prompt,
    _format_current_keywords_for_prompt,
    _format_current_topics_for_prompt,
    _format_extra_context_for_prompt,
    _format_keywords_for_prompt,
    _format_sample,
    _format_title_for_prompt,
    _format_topics_for_prompt,
)


class TestFormatSample:
    """Tests for _format_sample."""

    def test_empty_sample(self) -> None:
        """Test with None or empty list."""
        assert _format_sample(None) == "not available"
        assert _format_sample([]) == "not available"

    def test_single_row(self) -> None:
        """Test with single row."""
        sample = [{"name": "Alice", "age": 30}]
        result = _format_sample(sample)
        assert "Alice" in result
        assert "30" in result

    def test_multiple_rows(self) -> None:
        """Test with multiple rows."""
        sample = [
            {"id": 1, "status": "active"},
            {"id": 2, "status": "inactive"},
        ]
        result = _format_sample(sample)
        assert "1" in result
        assert "2" in result
        assert "active" in result
        assert "inactive" in result


class TestFormatColumnHeaders:
    """Tests for _format_column_headers."""

    def test_no_types(self) -> None:
        """Test without column types."""
        columns = ["id", "name", "email"]
        result = _format_column_headers(columns)
        assert result == "id, name, email"

    def test_with_types(self) -> None:
        """Test with column types."""
        columns = ["id", "name", "created"]
        types = {"id": "integer", "name": "string", "created": "date"}
        result = _format_column_headers(columns, types)
        assert "id (integer)" in result
        assert "name (string)" in result
        assert "created (date)" in result

    def test_partial_types(self) -> None:
        """Test with partial column types."""
        columns = ["id", "name"]
        types = {"id": "integer"}
        result = _format_column_headers(columns, types)
        assert "id (integer)" in result
        assert "name" in result
        assert result.count("(") == 1


class TestFormatKeywordsForPrompt:
    """Tests for _format_keywords_for_prompt."""

    def test_none_keywords(self) -> None:
        """Test with None."""
        assert _format_keywords_for_prompt(None) == ""

    def test_empty_keywords(self) -> None:
        """Test with empty list."""
        assert _format_keywords_for_prompt([]) == ""

    def test_single_keyword(self) -> None:
        """Test with single keyword."""
        keywords = ["water"]
        assert _format_keywords_for_prompt(keywords) == "water"

    def test_multiple_keywords(self) -> None:
        """Test with multiple keywords."""
        keywords = ["water", "river", "flood"]
        result = _format_keywords_for_prompt(keywords)
        assert "water" in result
        assert "river" in result
        assert "flood" in result

    def test_deduplication(self) -> None:
        """Test deduplication of keywords."""
        keywords = ["water", "water", "river", "river"]
        result = _format_keywords_for_prompt(keywords)
        assert result.count("water") == 1
        assert result.count("river") == 1

    def test_whitespace_trimming(self) -> None:
        """Test trimming of whitespace."""
        keywords = ["  water  ", " river ", "flood"]
        result = _format_keywords_for_prompt(keywords)
        assert "  " not in result
        assert "water" in result
        assert "river" in result

    def test_max_keywords_cap(self) -> None:
        """Test that keywords are capped at _MAX_PROMPT_KEYWORDS."""
        # Create 150 keywords to exceed the cap (100)
        keywords = [f"keyword_{i}" for i in range(150)]
        result = _format_keywords_for_prompt(keywords)
        # Count commas + 1 to get number of keywords
        keyword_count = result.count(", ") + 1 if result else 0
        assert keyword_count <= 100


class TestFormatTitleForPrompt:
    """Tests for _format_title_for_prompt."""

    def test_title_only(self) -> None:
        """Test with title provided."""
        result = _format_title_for_prompt("table", "My Title", None)
        assert result == "My Title"

    def test_fallback_to_table_name(self) -> None:
        """Test fallback to table name."""
        result = _format_title_for_prompt("my_table", None, None)
        assert result == "my_table"

    def test_current_values_priority(self) -> None:
        """Test that current_values takes priority."""
        current = {"title": "Current Title"}
        result = _format_title_for_prompt("table", "New Title", current)
        assert result == "Current Title"


class TestFormatBboxForPrompt:
    """Tests for _format_bbox_for_prompt."""

    def test_with_bbox(self) -> None:
        """Test with bbox provided."""
        bbox = "BOX(0 0, 10 10)"
        assert _format_bbox_for_prompt(bbox) == bbox

    def test_without_bbox(self) -> None:
        """Test without bbox."""
        assert _format_bbox_for_prompt(None) == "not available"


class TestFormatCurrentAbstractForPrompt:
    """Tests for _format_current_abstract_for_prompt."""

    def test_with_abstract(self) -> None:
        """Test with abstract in current_values."""
        current = {"abstract": "This is a dataset"}
        result = _format_current_abstract_for_prompt(current)
        assert result == "This is a dataset"

    def test_without_abstract(self) -> None:
        """Test without abstract."""
        assert _format_current_abstract_for_prompt(None) == ""
        assert _format_current_abstract_for_prompt({}) == ""


class TestFormatCurrentKeywordsForPrompt:
    """Tests for _format_current_keywords_for_prompt."""

    def test_with_keywords(self) -> None:
        """Test with keywords in current_values."""
        current = {"keywords": "water, river, flood"}
        result = _format_current_keywords_for_prompt(current)
        assert result == "water, river, flood"

    def test_without_keywords(self) -> None:
        """Test without keywords."""
        assert _format_current_keywords_for_prompt(None) == ""
        assert _format_current_keywords_for_prompt({}) == ""


class TestFormatCurrentTopicsForPrompt:
    """Tests for _format_current_topics_for_prompt."""

    def test_with_topics(self) -> None:
        """Test with topics in current_values."""
        current = {"topics": "environment, hydrology"}
        result = _format_current_topics_for_prompt(current)
        assert result == "environment, hydrology"

    def test_without_topics(self) -> None:
        """Test without topics."""
        assert _format_current_topics_for_prompt(None) == ""
        assert _format_current_topics_for_prompt({}) == ""


class TestFormatTopicsForPrompt:
    """Tests for _format_topics_for_prompt."""

    def test_with_topics(self) -> None:
        """Test with topics list."""
        topics = ["environment", "hydrology"]
        result = _format_topics_for_prompt(topics)
        assert "environment" in result
        assert "hydrology" in result

    def test_without_topics(self) -> None:
        """Test without topics."""
        assert _format_topics_for_prompt(None) == ""
        assert _format_topics_for_prompt([]) == ""


class TestFormatExtraContextForPrompt:
    """Tests for _format_extra_context_for_prompt."""

    def test_with_string_context(self) -> None:
        """Test with string context."""
        context = "Additional information"
        result = _format_extra_context_for_prompt(context)
        assert result == context

    def test_with_dict_context(self) -> None:
        """Test with dict context."""
        context = {"key": "value"}
        result = _format_extra_context_for_prompt(context)
        assert result == context

    def test_without_context(self) -> None:
        """Test without context."""
        assert _format_extra_context_for_prompt(None) == ""
