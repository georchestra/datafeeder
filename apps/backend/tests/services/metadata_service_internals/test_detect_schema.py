from unittest.mock import MagicMock, patch

from src.services.metadata_schema import NoopSchema
from src.services.metadata_schema_19115_3 import Iso19115_3Schema
from src.services.metadata_schema_19139 import Iso19139Schema
from src.services.metadata_service import MetadataService
from tests.services.metadata_service_internals.samples import (
    SAMPLE_19115_3_NO_REVISION,
    SAMPLE_19139_NO_REVISION,
)


class TestDetectSchema:
    @patch("src.services.metadata_service.GnApi")
    def test_detects_19115_3(self, mock_gn_api: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.get_metadataxml.return_value = SAMPLE_19115_3_NO_REVISION
        mock_gn_api.return_value = mock_api

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test")
        schema = service.detect_schema("uuid-123")

        assert isinstance(schema, Iso19115_3Schema)
        mock_api.get_metadataxml.assert_called_once_with("uuid-123")

    @patch("src.services.metadata_service.GnApi")
    def test_detects_19139(self, mock_gn_api: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.get_metadataxml.return_value = SAMPLE_19139_NO_REVISION
        mock_gn_api.return_value = mock_api

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test")
        schema = service.detect_schema("uuid-123")

        assert isinstance(schema, Iso19139Schema)

    @patch("src.services.metadata_service.GnApi")
    def test_returns_noop_for_unsupported(self, mock_gn_api: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.get_metadataxml.return_value = b"<root/>"
        mock_gn_api.return_value = mock_api

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test")
        schema = service.detect_schema("uuid-123")

        assert isinstance(schema, NoopSchema)

    @patch("src.services.metadata_service.GnApi")
    def test_returns_noop_when_fetch_fails(self, mock_gn_api: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.get_metadataxml.side_effect = RuntimeError("boom")
        mock_gn_api.return_value = mock_api

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test")
        schema = service.detect_schema("uuid-123")

        assert isinstance(schema, NoopSchema)


class TestDetectSchemaFromXml:
    def test_detects_19115_3(self) -> None:
        schema = MetadataService.detect_schema_from_xml(SAMPLE_19115_3_NO_REVISION)

        assert isinstance(schema, Iso19115_3Schema)

    def test_detects_19139(self) -> None:
        schema = MetadataService.detect_schema_from_xml(SAMPLE_19139_NO_REVISION)

        assert isinstance(schema, Iso19139Schema)

    def test_returns_noop_for_unsupported(self) -> None:
        schema = MetadataService.detect_schema_from_xml(b"<root/>")

        assert isinstance(schema, NoopSchema)
