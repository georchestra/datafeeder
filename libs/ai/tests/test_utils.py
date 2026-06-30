"""Unit tests for utils module."""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from ai.utils import load_prompt, pg_type_to_iso19110


class TestLoadPrompt:
    """Tests for load_prompt function."""

    def test_load_from_default_prompts_dir(self) -> None:
        """Test loading a prompt from the default prompts directory."""
        # Assuming metadata_system.md or similar exists in the prompts dir
        # This test ensures the function can load without errors
        try:
            result = load_prompt(default="metadata_system.md")
            assert isinstance(result, str)
            assert len(result) > 0
        except FileNotFoundError:
            pytest.skip("Prompt file not found (expected in dev environment)")

    def test_load_from_custom_path(self) -> None:
        """Test loading a prompt from a custom path."""
        with TemporaryDirectory() as tmpdir:
            # Create a temporary prompt file
            tmp_path = Path(tmpdir) / "test_prompt.txt"
            tmp_path.write_text("This is a test prompt content")

            result = load_prompt(path=str(tmp_path))
            assert result == "This is a test prompt content"

    def test_load_with_custom_path_takes_priority(self) -> None:
        """Test that custom path takes priority over default."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "custom_prompt.txt"
            tmp_path.write_text("Custom content")

            # Even if we specify a default, custom path should be used
            result = load_prompt(path=str(tmp_path), default="nonexistent.md")
            assert result == "Custom content"

    def test_load_strips_whitespace(self) -> None:
        """Test that loaded content is stripped."""
        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir) / "test_prompt.txt"
            tmp_path.write_text("  \n  Prompt content  \n  ")

            result = load_prompt(path=str(tmp_path))
            assert result == "Prompt content"

    def test_load_raises_error_when_neither_path_nor_default(self) -> None:
        """Test that error is raised when neither path nor default is provided."""
        with pytest.raises(ValueError):
            load_prompt()

    def test_load_raises_error_when_file_not_found(self) -> None:
        """Test that error is raised when file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            load_prompt(path="/nonexistent/path/to/file.txt")


class TestPgTypeToIso19110:
    """Tests for pg_type_to_iso19110 function."""

    def test_varchar_types(self) -> None:
        """Test VARCHAR type conversion."""
        assert pg_type_to_iso19110("VARCHAR") == "string"
        assert pg_type_to_iso19110("VARCHAR(255)") == "string (255)"
        assert pg_type_to_iso19110("VARCHAR(50)") == "string (50)"

    def test_integer_types(self) -> None:
        """Test INTEGER type conversion."""
        assert pg_type_to_iso19110("INTEGER") == "integer"
        assert pg_type_to_iso19110("INT") == "integer"
        assert pg_type_to_iso19110("BIGINT") == "integer"
        assert pg_type_to_iso19110("SMALLINT") == "integer"

    def test_numeric_types(self) -> None:
        """Test NUMERIC type conversion."""
        assert pg_type_to_iso19110("NUMERIC") == "number"
        assert pg_type_to_iso19110("DECIMAL") == "number"
        assert pg_type_to_iso19110("NUMERIC(10,2)") == "number"
        assert pg_type_to_iso19110("DOUBLE PRECISION") == "number"

    def test_boolean_types(self) -> None:
        """Test BOOLEAN type conversion."""
        assert pg_type_to_iso19110("BOOLEAN") == "boolean"
        assert pg_type_to_iso19110("BOOL") == "boolean"

    def test_date_types(self) -> None:
        """Test DATE/TIME type conversion."""
        assert pg_type_to_iso19110("DATE") == "date"
        assert pg_type_to_iso19110("TIMESTAMP") == "date"
        assert pg_type_to_iso19110("TIMESTAMP WITH TIME ZONE") == "date"
        assert pg_type_to_iso19110("TIME") == "date"

    def test_json_types(self) -> None:
        """Test JSON type conversion."""
        assert pg_type_to_iso19110("JSON") == "string"
        assert pg_type_to_iso19110("JSONB") == "string"

    def test_array_types(self) -> None:
        """Test ARRAY type conversion."""
        assert pg_type_to_iso19110("INTEGER[]") == "integer"
        assert pg_type_to_iso19110("VARCHAR[]") == "string"

    def test_text_type(self) -> None:
        """Test TEXT type conversion."""
        assert pg_type_to_iso19110("TEXT") == "string"

    def test_geometry_types(self) -> None:
        """Test geometry type conversion."""
        assert pg_type_to_iso19110("POINT") == "GM_Point"
        assert pg_type_to_iso19110("LINESTRING") == "GM_LineString"
        assert pg_type_to_iso19110("POLYGON") == "GM_Polygon"
        assert pg_type_to_iso19110("MULTIPOINT") == "GM_MultiPoint"
        assert pg_type_to_iso19110("MULTILINESTRING") == "GM_MultiLineString"
        assert pg_type_to_iso19110("MULTIPOLYGON") == "GM_MultiPolygon"
        assert pg_type_to_iso19110("GEOMETRY") == "GM_Geometry"

    def test_unknown_type_fallback(self) -> None:
        """Test fallback for unknown types."""
        result = pg_type_to_iso19110("UNKNOWN_TYPE")
        assert result == "string"  # Default fallback

    def test_case_insensitive(self) -> None:
        """Test that type conversion is case-insensitive."""
        assert pg_type_to_iso19110("varchar(100)") == pg_type_to_iso19110("VARCHAR(100)")
        assert pg_type_to_iso19110("integer") == pg_type_to_iso19110("INTEGER")
        assert pg_type_to_iso19110("point") == pg_type_to_iso19110("POINT")

    def test_whitespace_handling(self) -> None:
        """Test handling of extra whitespace."""
        assert pg_type_to_iso19110("  VARCHAR(50)  ") == "string (50)"
        assert pg_type_to_iso19110("INTEGER ") == "integer"
