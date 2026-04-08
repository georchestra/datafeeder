from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from src.models.data_import import FileType
from src.services.files import (
    delete_temp_file,
    get_temp_file_url,
    strip_file_extension,
    upload_file_to_temp,
)


class TestStripFileExtension:
    def test_returns_none_for_none(self) -> None:
        assert strip_file_extension(None) is None

    def test_no_extension_unchanged(self) -> None:
        assert strip_file_extension("myfile") == "myfile"

    def test_strips_simple_extension(self) -> None:
        assert strip_file_extension("data.csv") == "data"

    def test_strips_last_extension_only(self) -> None:
        assert strip_file_extension("archive.data.csv") == "archive.data"

    def test_strips_extension_with_spaces_in_name(self) -> None:
        assert strip_file_extension("station_reunion (1).csv") == "station_reunion (1)"

    def test_strips_geojson_extension(self) -> None:
        assert strip_file_extension("my_layer.geojson") == "my_layer"

    def test_strips_shapefile_extension(self) -> None:
        assert strip_file_extension("communes.shp") == "communes"

    def test_strips_geopackage_extension(self) -> None:
        assert strip_file_extension("data.gpkg") == "data"

    def test_hidden_file_dot_prefix_unchanged(self) -> None:
        assert strip_file_extension(".gitignore") == ".gitignore"

    def test_hidden_file_with_extension(self) -> None:
        assert strip_file_extension(".hidden.csv") == ".hidden"

    def test_empty_string_unchanged(self) -> None:
        assert strip_file_extension("") == ""

    def test_dot_only_unchanged(self) -> None:
        assert strip_file_extension(".") == "."


class TestUploadFileToTemp:
    """Test cases for upload_file_to_temp function."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.TMP_UPLOAD_PATH = "/tmp"
        settings.BACKEND_URL = "http://localhost:8000"
        return settings

    @pytest.fixture
    def mock_upload_file(self) -> MagicMock:
        """Create a mock UploadFile."""
        file = MagicMock(spec=UploadFile)
        file.filename = "test_file.json"
        file.content_type = "application/json"
        file.read = AsyncMock(return_value=b'{"test": "data"}')
        return file

    @pytest.mark.asyncio
    @patch("src.services.files.get_settings")
    @patch("src.services.files.Path")
    async def test_upload_file_success(
        self,
        mock_path: MagicMock,
        mock_get_settings: MagicMock,
        mock_settings: MagicMock,
        mock_upload_file: MagicMock,
    ) -> None:
        """Test successful file upload."""
        mock_get_settings.return_value = mock_settings

        # Mock Path behavior for original filename parsing
        mock_original_path = MagicMock()
        mock_original_path.stem = "test_file"
        mock_original_path.suffix = ".json"

        # Mock Path behavior for tmp directory and file path
        mock_tmp_path = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.exists = MagicMock(return_value=True)
        mock_file_path.write_bytes = MagicMock()
        mock_tmp_path.__truediv__ = MagicMock(return_value=mock_file_path)
        mock_tmp_path.mkdir = MagicMock()

        # Configure Path mock to return different objects based on call
        mock_path.side_effect = [mock_tmp_path, mock_original_path]

        source_file_name, source_file_type, file_url = await upload_file_to_temp(mock_upload_file)

        # Verify the file was read
        mock_upload_file.read.assert_called_once()

        # Verify the tmp directory was created
        mock_tmp_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)

        # Verify the file content was written
        mock_file_path.write_bytes.assert_called_once_with(b'{"test": "data"}')

        # Verify result contains the filename with unique ID
        assert source_file_name.startswith("test_file")
        assert source_file_name.endswith(".json")
        assert source_file_type == FileType.JSON
        assert file_url.startswith("http://localhost:8000/internal/files/test_file")
        assert file_url.endswith(".json")

    @pytest.mark.asyncio
    @patch("src.services.files.get_settings")
    @patch("src.services.files.Path")
    async def test_upload_file_with_zip(
        self, mock_path: MagicMock, mock_get_settings: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test file upload with zip extension."""
        mock_get_settings.return_value = mock_settings

        # Create mock zip file
        zip_file = MagicMock(spec=UploadFile)
        zip_file.filename = "archive.zip"
        zip_file.content_type = "application/zip"
        zip_file.read = AsyncMock(return_value=b"fake zip content")

        # Mock Path behavior for original filename parsing
        mock_original_path = MagicMock()
        mock_original_path.stem = "archive"
        mock_original_path.suffix = ".zip"

        # Mock Path behavior for tmp directory and file path
        mock_tmp_path = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.exists = MagicMock(return_value=True)
        mock_file_path.write_bytes = MagicMock()
        mock_tmp_path.__truediv__ = MagicMock(return_value=mock_file_path)
        mock_tmp_path.mkdir = MagicMock()

        mock_path.side_effect = [mock_tmp_path, mock_original_path]

        source_file_name, source_file_type, file_url = await upload_file_to_temp(zip_file)

        # Verify result has .zip extension
        assert source_file_name.endswith(".zip")
        assert source_file_type == FileType.ZIP
        assert file_url.endswith(".zip")
        mock_file_path.write_bytes.assert_called_once_with(b"fake zip content")

    @pytest.mark.asyncio
    @patch("src.services.files.get_settings")
    @patch("src.services.files.Path")
    async def test_upload_file_no_filename(
        self, mock_path: MagicMock, mock_get_settings: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test file upload when no filename is provided."""
        mock_get_settings.return_value = mock_settings

        # Create mock file without filename
        file = MagicMock(spec=UploadFile)
        file.filename = None
        file.content_type = "text/csv"
        file.read = AsyncMock(return_value=b"content")

        # Mock Path behavior for original filename parsing
        mock_original_path = MagicMock()
        mock_original_path.stem = "uploaded_file"
        mock_original_path.suffix = ".csv"

        # Mock Path behavior for tmp directory and file path
        mock_tmp_path = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.exists = MagicMock(return_value=True)
        mock_file_path.write_bytes = MagicMock()
        mock_tmp_path.__truediv__ = MagicMock(return_value=mock_file_path)
        mock_tmp_path.mkdir = MagicMock()

        mock_path.side_effect = [mock_tmp_path, mock_original_path]

        source_file_name, source_file_type, file_url = await upload_file_to_temp(file)

        # Verify default filename is used with extension
        assert source_file_name.startswith("uploaded_file")
        assert source_file_name.endswith(".csv")
        assert source_file_type == FileType.CSV
        assert file_url.startswith("http://localhost:8000/internal/files/uploaded_file")

    @pytest.mark.asyncio
    @patch("src.services.files.get_settings")
    @patch("src.services.files.Path")
    async def test_upload_file_empty_content(
        self,
        mock_path: MagicMock,
        mock_get_settings: MagicMock,
        mock_settings: MagicMock,
        mock_upload_file: MagicMock,
    ) -> None:
        """Test file upload with empty content raises error."""
        mock_get_settings.return_value = mock_settings
        mock_upload_file.read = AsyncMock(return_value=b"")

        # Mock Path behavior for original filename parsing
        mock_original_path = MagicMock()
        mock_original_path.stem = "test_file"
        mock_original_path.suffix = ".json"

        # Mock Path behavior for tmp directory
        mock_tmp_path = MagicMock()
        mock_path.side_effect = [mock_tmp_path, mock_original_path]

        with pytest.raises(ValueError, match="Empty file uploaded"):
            await upload_file_to_temp(mock_upload_file)

    @pytest.mark.asyncio
    @patch("src.services.files.get_settings")
    @patch("src.services.files.Path")
    async def test_upload_file_write_failure(
        self,
        mock_path: MagicMock,
        mock_get_settings: MagicMock,
        mock_settings: MagicMock,
        mock_upload_file: MagicMock,
    ) -> None:
        """Test file upload when write fails."""
        mock_get_settings.return_value = mock_settings

        # Mock Path behavior for original filename parsing
        mock_original_path = MagicMock()
        mock_original_path.stem = "test_file"
        mock_original_path.suffix = ".json"

        # Mock Path behavior with write failure
        mock_tmp_path = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.write_bytes = MagicMock(side_effect=IOError("Disk full"))
        mock_file_path.exists = MagicMock(return_value=True)
        mock_file_path.unlink = MagicMock()
        mock_tmp_path.__truediv__ = MagicMock(return_value=mock_file_path)
        mock_tmp_path.mkdir = MagicMock()

        mock_path.side_effect = [mock_tmp_path, mock_original_path]

        with pytest.raises(ValueError, match="Failed to save uploaded file"):
            await upload_file_to_temp(mock_upload_file)

        # Verify cleanup was attempted
        mock_file_path.unlink.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.files.get_settings")
    @patch("src.services.files.Path")
    async def test_upload_file_not_created(
        self,
        mock_path: MagicMock,
        mock_get_settings: MagicMock,
        mock_settings: MagicMock,
        mock_upload_file: MagicMock,
    ) -> None:
        """Test file upload when file is not created after write."""
        mock_get_settings.return_value = mock_settings

        # Mock Path behavior for original filename parsing
        mock_original_path = MagicMock()
        mock_original_path.stem = "test_file"
        mock_original_path.suffix = ".json"

        # Mock Path behavior where file doesn't exist after write
        mock_tmp_path = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.exists = MagicMock(return_value=False)
        mock_file_path.write_bytes = MagicMock()
        mock_tmp_path.__truediv__ = MagicMock(return_value=mock_file_path)
        mock_tmp_path.mkdir = MagicMock()

        mock_path.side_effect = [mock_tmp_path, mock_original_path]

        # The IOError is caught and re-raised as ValueError
        with pytest.raises(ValueError, match="Failed to save uploaded file"):
            await upload_file_to_temp(mock_upload_file)


class TestGetTempFileUrl:
    """Test cases for get_temp_file_url function."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.BACKEND_URL = "http://localhost:8000"
        return settings

    @patch("src.services.files.get_settings")
    def test_get_temp_file_url(
        self, mock_get_settings: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test generating URL for a temporary file."""
        mock_get_settings.return_value = mock_settings
        filename = "test_file_abc123.json"

        result = get_temp_file_url(filename)

        assert result == "http://localhost:8000/internal/files/test_file_abc123.json"

    @patch("src.services.files.get_settings")
    def test_get_temp_file_url_different_backend(self, mock_get_settings: MagicMock) -> None:
        """Test generating URL with different backend URL."""
        settings = MagicMock()
        settings.BACKEND_URL = "https://example.com/api"
        mock_get_settings.return_value = settings
        filename = "data.csv"

        result = get_temp_file_url(filename)

        assert result == "https://example.com/api/internal/files/data.csv"

    @patch("src.services.files.get_settings")
    def test_get_temp_file_url_special_characters(
        self, mock_get_settings: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test generating URL with special characters in filename."""
        mock_get_settings.return_value = mock_settings
        filename = "file with spaces_123.txt"

        result = get_temp_file_url(filename)

        # Note: URL encoding is not performed by the function
        assert result == "http://localhost:8000/internal/files/file with spaces_123.txt"


class TestDeleteTempFile:
    """Test cases for delete_temp_file function."""

    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        """Create mock settings."""
        settings = MagicMock()
        settings.TMP_UPLOAD_PATH = "/tmp"
        settings.BACKEND_URL = "http://localhost:8000"
        return settings

    @patch("src.services.files.get_settings")
    @patch("src.services.files.Path")
    def test_delete_temp_file_success(
        self, mock_path: MagicMock, mock_get_settings: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test successful file deletion."""
        mock_get_settings.return_value = mock_settings

        # Mock Path behavior
        mock_tmp_path = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.exists = MagicMock(return_value=True)
        mock_file_path.unlink = MagicMock()
        mock_tmp_path.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path.return_value = mock_tmp_path

        delete_temp_file("http://localhost:8000/internal/files/test_file.json")
        mock_file_path.exists.assert_called_once()
        mock_file_path.unlink.assert_called_once()

    @patch("src.services.files.get_settings")
    @patch("src.services.files.Path")
    def test_delete_temp_file_not_found(
        self, mock_path: MagicMock, mock_get_settings: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test deleting a file that doesn't exist."""
        mock_get_settings.return_value = mock_settings

        # Mock Path behavior for non-existent file
        mock_tmp_path = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.exists = MagicMock(return_value=False)
        mock_file_path.unlink = MagicMock()
        mock_tmp_path.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path.return_value = mock_tmp_path

        with pytest.raises(IOError):
            delete_temp_file("http://localhost:8000/internal/files/nonexistent.json")

        mock_file_path.exists.assert_called_once()
        mock_file_path.unlink.assert_not_called()

    @patch("src.services.files.get_settings")
    @patch("src.services.files.Path")
    def test_delete_temp_file_unlink_error(
        self, mock_path: MagicMock, mock_get_settings: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Test handling of unlink errors."""
        mock_get_settings.return_value = mock_settings

        # Mock Path behavior with unlink error
        mock_tmp_path = MagicMock()
        mock_file_path = MagicMock()
        mock_file_path.exists = MagicMock(return_value=True)
        mock_file_path.unlink = MagicMock(side_effect=PermissionError("Permission denied"))
        mock_tmp_path.__truediv__ = MagicMock(return_value=mock_file_path)

        mock_path.return_value = mock_tmp_path

        with pytest.raises(PermissionError):
            delete_temp_file("http://localhost:8000/internal/files/protected_file.json")

        mock_file_path.exists.assert_called_once()
        mock_file_path.unlink.assert_called_once()
