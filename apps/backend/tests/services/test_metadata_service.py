from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from lxml import etree

from src.models.integrity_link import IntegrityLink
from src.services.metadata_service import MetadataService


class TestMetadataService:
    @pytest.fixture
    def sample_integrity_link(self):
        """Create sample IntegrityLink for testing."""
        return IntegrityLink(
            id=uuid4(),
            integrity_title="Test Dataset",
            integrity_owner="testuser",
            integrity_organization="Test Org",
            final_table_name="test_table",
            staging_table_name="staging_test_table",
            created_at=datetime.now(timezone.utc),
            last_retrieval_timestamp=datetime.now(timezone.utc),
        )

    @patch("src.services.metadata_service.GnApi")
    def test_metadata_service_initialization(self, mock_gn_api):
        """Test MetadataService initialization."""
        service = MetadataService(
            gn_api_url="http://test.example.com/geonetwork/srv/api",
            datadir_path="/home/aabt/Sites/DataKern/docker/datadir",
            credentials=None,
            verify_tls=False,
        )

        assert service.template_path.endswith("metadata_template-19115-3.xml")
        assert service.xslt_path.endswith("metadata_transform-19115-3.xsl")
        mock_gn_api.assert_called_once()

    @patch("src.services.metadata_service.etree.parse")
    @patch("src.services.metadata_service.GnApi")
    def test_generate_metadata(self, mock_gn_api, mock_parse, sample_integrity_link):
        """Test metadata XML generation."""
        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        # Mock XML parsing
        mock_xml_doc = MagicMock()
        mock_xslt_doc = MagicMock()
        mock_transform = MagicMock()
        mock_transform.return_value = etree.fromstring("<root>test</root>")

        mock_parse.side_effect = [mock_xml_doc, mock_xslt_doc]

        with patch("src.services.metadata_service.etree.XSLT", return_value=mock_transform):
            metadata_xml = service.generate_metadata(sample_integrity_link)

            assert metadata_xml is not None
            assert isinstance(metadata_xml, str)

    @patch("src.services.metadata_service.GnApi")
    def test_publish_metadata_success(self, mock_gn_api):
        """Test successful metadata publication."""
        expected_uuid = "123e4567-e89b-12d3-a456-426614174000"

        # Mock Response object with json() method
        mock_response = MagicMock()
        mock_response.json.return_value = {"uuid": expected_uuid}

        mock_api_instance = MagicMock()
        mock_api_instance.upload_metadata.return_value = mock_response
        mock_gn_api.return_value = mock_api_instance

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        result_uuid = service.publish_metadata("<mock_metadata/>")

        assert result_uuid == expected_uuid
        mock_api_instance.upload_metadata.assert_called_once()

    @patch("src.services.metadata_service.GnApi")
    def test_publish_metadata_handles_geonetwork_error(self, mock_gn_api):
        """Test error handling when GeoNetwork is unavailable."""
        mock_api_instance = MagicMock()
        mock_api_instance.upload_metadata.side_effect = Exception("Connection refused")
        mock_gn_api.return_value = mock_api_instance

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        with pytest.raises(Exception, match="Connection refused"):
            service.publish_metadata("<mock_metadata/>")

    @patch("src.services.metadata_service.etree.parse")
    @patch("src.services.metadata_service.GnApi")
    def test_create_and_publish_metadata_integration(
        self, mock_gn_api, mock_parse, sample_integrity_link
    ):
        """Test full workflow: generate + publish."""
        expected_uuid = "metadata-uuid-123"

        # Mock Response object with json() method
        mock_response = MagicMock()
        mock_response.json.return_value = {"uuid": expected_uuid}

        mock_api_instance = MagicMock()
        mock_api_instance.upload_metadata.return_value = mock_response
        mock_gn_api.return_value = mock_api_instance

        # Mock XML parsing
        mock_xml_doc = MagicMock()
        mock_xslt_doc = MagicMock()
        mock_transform = MagicMock()
        mock_transform.return_value = etree.fromstring("<root>test</root>")

        mock_parse.side_effect = [mock_xml_doc, mock_xslt_doc]

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        with patch("src.services.metadata_service.etree.XSLT", return_value=mock_transform):
            result_uuid = service.create_and_publish_metadata(sample_integrity_link)

            assert result_uuid == expected_uuid
