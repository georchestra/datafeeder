from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from lxml import etree

from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.services.metadata_service import MetadataService


class TestMetadataService:
    @pytest.fixture
    def sample_integrity_link(self) -> IntegrityLink:
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
            source_import_type=ImportType.URL,
        )

    @patch("src.services.metadata_service.GnApi")
    def test_metadata_service_initialization(self, mock_gn_api: MagicMock) -> None:
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
    def test_generate_metadata(
        self, mock_gn_api: MagicMock, mock_parse: MagicMock, sample_integrity_link: IntegrityLink
    ) -> None:
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
    def test_publish_metadata_success(self, mock_gn_api: MagicMock) -> None:
        """Test successful metadata publication uses OVERWRITE and private by default."""
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
        mock_api_instance.upload_metadata.assert_called_once_with(
            metadata="<mock_metadata/>",
            groupid="100",
            uuidprocessing="OVERWRITE",
            publish=False,
        )

    @patch("src.services.metadata_service.GnApi")
    def test_publish_metadata_handles_geonetwork_error(self, mock_gn_api: MagicMock) -> None:
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
        self, mock_gn_api: MagicMock, mock_parse: MagicMock, sample_integrity_link: IntegrityLink
    ) -> None:
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

    @patch("src.services.metadata_service.GnApi")
    def test_set_record_ownership_success(self, mock_gn_api: MagicMock) -> None:
        """Test successful ownership assignment."""
        mock_session = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.session = mock_session
        mock_api_instance.api_url = "http://test/api"
        mock_gn_api.return_value = mock_api_instance

        # Mock users response
        users_response = MagicMock()
        users_response.json.return_value = [
            {"id": 1, "username": "admin"},
            {"id": 42, "username": "testuser"},
        ]

        # Mock groups response
        groups_response = MagicMock()
        groups_response.json.return_value = [
            {"id": 10, "name": "sample"},
            {"id": 20, "name": "Test Org"},
        ]

        # Mock ownership response
        ownership_response = MagicMock()

        mock_session.get.side_effect = [users_response, groups_response]
        mock_session.put.return_value = ownership_response

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        service.set_record_ownership("some-uuid", "testuser", "test org")

        # Verify the PUT call with correct IDs
        mock_session.put.assert_called_once_with(
            "http://test/api/records/some-uuid/ownership",
            params={"groupIdentifier": 20, "userIdentifier": 42},
        )

    @patch("src.services.metadata_service.GnApi")
    def test_set_record_ownership_user_not_found(self, mock_gn_api: MagicMock) -> None:
        """Test ownership skipped when user not found."""
        mock_session = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.session = mock_session
        mock_api_instance.api_url = "http://test/api"
        mock_gn_api.return_value = mock_api_instance

        users_response = MagicMock()
        users_response.json.return_value = [{"id": 1, "username": "admin"}]

        groups_response = MagicMock()
        groups_response.json.return_value = [{"id": 10, "name": "Test Org"}]

        mock_session.get.side_effect = [users_response, groups_response]

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        # Should not raise, just warn and skip
        service.set_record_ownership("some-uuid", "unknown_user", "Test Org")

        # PUT should never be called
        mock_session.put.assert_not_called()

    @patch("src.services.metadata_service.GnApi")
    def test_set_record_ownership_group_not_found(self, mock_gn_api: MagicMock) -> None:
        """Test ownership skipped when group not found."""
        mock_session = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.session = mock_session
        mock_api_instance.api_url = "http://test/api"
        mock_gn_api.return_value = mock_api_instance

        users_response = MagicMock()
        users_response.json.return_value = [{"id": 42, "username": "testuser"}]

        groups_response = MagicMock()
        groups_response.json.return_value = [{"id": 10, "name": "Other Org"}]

        mock_session.get.side_effect = [users_response, groups_response]

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        service.set_record_ownership("some-uuid", "testuser", "Missing Org")

        mock_session.put.assert_not_called()
