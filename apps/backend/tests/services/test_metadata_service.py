from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from lxml import etree

from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import RuleValue
from src.services.metadata_service import (
    NS_19115_3,
    NS_19139,
    MetadataService,
)


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
            datadir_path="/home/aabt/Sites/Datafeeder/docker/datadir",
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

    @patch("src.services.metadata_service.GnApi")
    def test_set_record_ownership_user_groups_mode(self, mock_gn_api: MagicMock) -> None:
        """Test gn_sync_mode="ROLE" uses user's first non-system group."""
        mock_session = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.session = mock_session
        mock_api_instance.api_url = "http://test/api"
        mock_gn_api.return_value = mock_api_instance

        # Mock users response
        users_response = MagicMock()
        users_response.json.return_value = [{"id": 42, "username": "testuser"}]

        # Mock user groups response (GN 4.x format)
        user_groups_response = MagicMock()
        user_groups_response.json.return_value = [
            {"id": {"groupId": 1, "userId": 42}, "profile": "RegisteredUser"},
            {"id": {"groupId": 15, "userId": 42}, "profile": "Editor"},
            {"id": {"groupId": 20, "userId": 42}, "profile": "Editor"},
        ]

        ownership_response = MagicMock()

        mock_session.get.side_effect = [users_response, user_groups_response]
        mock_session.put.return_value = ownership_response

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
            gn_sync_mode="ROLE",
        )

        # group_name param is ignored in user-groups mode
        service.set_record_ownership("some-uuid", "testuser", "Ignored Org")

        mock_session.put.assert_called_once_with(
            "http://test/api/records/some-uuid/ownership",
            params={"groupIdentifier": 15, "userIdentifier": 42},
        )

    @patch("src.services.metadata_service.GnApi")
    def test_set_record_ownership_user_groups_fallback(self, mock_gn_api: MagicMock) -> None:
        """Test gn_sync_mode="ROLE" falls back to default group when user has only system groups."""
        mock_session = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.session = mock_session
        mock_api_instance.api_url = "http://test/api"
        mock_gn_api.return_value = mock_api_instance

        # Mock users response
        users_response = MagicMock()
        users_response.json.return_value = [{"id": 42, "username": "testuser"}]

        # Mock user groups: only system groups (id <= 2)
        user_groups_response = MagicMock()
        user_groups_response.json.return_value = [
            {"id": {"groupId": 0, "userId": 42}, "profile": "RegisteredUser"},
            {"id": {"groupId": 2, "userId": 42}, "profile": "RegisteredUser"},
        ]

        # Mock fallback: GET /api/groups returns the default group
        groups_response = MagicMock()
        groups_response.json.return_value = [
            {"id": 10, "name": "sample"},
            {"id": 20, "name": "Other Org"},
        ]

        ownership_response = MagicMock()

        mock_session.get.side_effect = [users_response, user_groups_response, groups_response]
        mock_session.put.return_value = ownership_response

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
            gn_sync_mode="ROLE",
            metadata_default_group_name="sample",
        )

        service.set_record_ownership("some-uuid", "testuser", "Ignored Org")

        # Should fall back to "sample" group (id=10)
        mock_session.put.assert_called_once_with(
            "http://test/api/records/some-uuid/ownership",
            params={"groupIdentifier": 10, "userIdentifier": 42},
        )

    @patch("src.services.metadata_service.GnApi")
    def test_toggle_publish_metadata_record_publish(self, mock_gn_api: MagicMock) -> None:
        """Test successful publication of a metadata record."""
        mock_api_instance = MagicMock()
        mock_gn_api.return_value = mock_api_instance

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        service.toggle_publish_metadata_record("test-uuid-123", publish=True)

        mock_api_instance.put_publish_record.assert_called_once_with("test-uuid-123")
        mock_api_instance.put_unpublish_record.assert_not_called()

    @patch("src.services.metadata_service.GnApi")
    def test_toggle_publish_metadata_record_unpublish(self, mock_gn_api: MagicMock) -> None:
        """Test successful unpublication of a metadata record."""
        mock_api_instance = MagicMock()
        mock_gn_api.return_value = mock_api_instance

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        service.toggle_publish_metadata_record("test-uuid-456", publish=False)

        mock_api_instance.put_unpublish_record.assert_called_once_with("test-uuid-456")
        mock_api_instance.put_publish_record.assert_not_called()

    @patch("src.services.metadata_service.GnApi")
    def test_toggle_publish_metadata_record_publish_error(self, mock_gn_api: MagicMock) -> None:
        """Test that errors from put_publish_record are propagated."""
        mock_api_instance = MagicMock()
        mock_api_instance.put_publish_record.side_effect = Exception("GeoNetwork unavailable")
        mock_gn_api.return_value = mock_api_instance

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        with pytest.raises(Exception, match="GeoNetwork unavailable"):
            service.toggle_publish_metadata_record("test-uuid-789", publish=True)

    @patch("src.services.metadata_service.GnApi")
    def test_toggle_publish_metadata_record_unpublish_error(self, mock_gn_api: MagicMock) -> None:
        """Test that errors from put_unpublish_record are propagated."""
        mock_api_instance = MagicMock()
        mock_api_instance.put_unpublish_record.side_effect = Exception("Connection refused")
        mock_gn_api.return_value = mock_api_instance

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
        )

        with pytest.raises(Exception, match="Connection refused"):
            service.toggle_publish_metadata_record("test-uuid-000", publish=False)

    @patch("src.services.metadata_service.GnApi")
    def test_sync_record_sharing_read_privilege(self, mock_gn_api: MagicMock) -> None:
        """READ rule → view=True, editing=False, download=True."""
        mock_session = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.session = mock_session
        mock_api_instance.api_url = "http://test/api"
        mock_gn_api.return_value = mock_api_instance

        groups_response = MagicMock()
        groups_response.json.return_value = [{"id": 20, "name": "TestOrg"}]
        mock_session.get.return_value = groups_response

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test/datadir")

        service.sync_record_sharing("some-uuid", [("TestOrg", RuleValue.READ)])

        mock_api_instance.put_sharing_record.assert_called_once_with(
            "some-uuid",
            {
                "clear": True,
                "privileges": [
                    {
                        "group": 20,
                        "operations": {
                            "view": True,
                            "download": True,
                            "editing": False,
                            "notify": False,
                            "dynamic": False,
                            "featured": False,
                        },
                    }
                ],
            },
        )

    @patch("src.services.metadata_service.GnApi")
    def test_sync_record_sharing_write_privilege(self, mock_gn_api: MagicMock) -> None:
        """WRITE rule → view=True, editing=True, download=True."""
        mock_session = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.session = mock_session
        mock_api_instance.api_url = "http://test/api"
        mock_gn_api.return_value = mock_api_instance

        groups_response = MagicMock()
        groups_response.json.return_value = [{"id": 30, "name": "WriteOrg"}]
        mock_session.get.return_value = groups_response

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test/datadir")

        service.sync_record_sharing("some-uuid", [("WriteOrg", RuleValue.WRITE)])

        call_args = mock_api_instance.put_sharing_record.call_args
        ops = call_args[0][1]["privileges"][0]["operations"]
        assert ops["view"] is True
        assert ops["editing"] is True
        assert ops["download"] is True

    @patch("src.services.metadata_service.GnApi")
    def test_sync_record_sharing_always_sets_clear_true(self, mock_gn_api: MagicMock) -> None:
        """clear=True is always included even for empty privileges."""
        mock_api_instance = MagicMock()
        mock_gn_api.return_value = mock_api_instance

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test/datadir")

        service.sync_record_sharing("some-uuid", [])

        mock_api_instance.put_sharing_record.assert_called_once_with(
            "some-uuid", {"clear": True, "privileges": []}
        )

    @patch("src.services.metadata_service.GnApi")
    def test_sync_record_sharing_raises_on_unresolvable_group(self, mock_gn_api: MagicMock) -> None:
        """Org with no matching GN group raises ValueError."""
        mock_session = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.session = mock_session
        mock_api_instance.api_url = "http://test/api"
        mock_gn_api.return_value = mock_api_instance

        groups_response = MagicMock()
        groups_response.json.return_value = [{"id": 10, "name": "OtherOrg"}]
        mock_session.get.return_value = groups_response

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test/datadir")

        with pytest.raises(ValueError, match="No GN group found for org 'UnknownOrg'"):
            service.sync_record_sharing("some-uuid", [("UnknownOrg", RuleValue.READ)])

    @patch("src.services.metadata_service.GnApi")
    def test_sync_record_sharing_gn_error_is_raised(self, mock_gn_api: MagicMock) -> None:
        """GeoNetwork API errors are propagated to the caller."""
        mock_api_instance = MagicMock()
        mock_api_instance.put_sharing_record.side_effect = Exception("GN unavailable")
        mock_gn_api.return_value = mock_api_instance

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test/datadir")

        with pytest.raises(Exception, match="GN unavailable"):
            service.sync_record_sharing("some-uuid", [])

    @patch("src.services.metadata_service.GnApi")
    def test_set_record_ownership_user_groups_no_fallback(self, mock_gn_api: MagicMock) -> None:
        """Test gn_sync_mode="ROLE" with no groups and default group not found → PUT not called."""
        mock_session = MagicMock()
        mock_api_instance = MagicMock()
        mock_api_instance.session = mock_session
        mock_api_instance.api_url = "http://test/api"
        mock_gn_api.return_value = mock_api_instance

        # Mock users response
        users_response = MagicMock()
        users_response.json.return_value = [{"id": 42, "username": "testuser"}]

        # Mock user groups: empty
        user_groups_response = MagicMock()
        user_groups_response.json.return_value = []

        # Mock fallback: default group not found
        groups_response = MagicMock()
        groups_response.json.return_value = [{"id": 20, "name": "Other Org"}]

        mock_session.get.side_effect = [users_response, user_groups_response, groups_response]

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path="/test/datadir",
            gn_sync_mode="ROLE",
            metadata_default_group_name="nonexistent",
        )

        service.set_record_ownership("some-uuid", "testuser", "Ignored Org")

        mock_session.put.assert_not_called()


# ---------------------------------------------------------------------------
# Helpers for revision-date tests
# ---------------------------------------------------------------------------

_SAMPLE_19115_3_NO_REVISION = b"""\
<mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                 xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                 xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0"
                 xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0">
  <mdb:dateInfo>
    <cit:CI_Date>
      <cit:date><gco:DateTime>2024-01-01T00:00:00</gco:DateTime></cit:date>
      <cit:dateType>
        <cit:CI_DateTypeCode codeList="x" codeListValue="creation"/>
      </cit:dateType>
    </cit:CI_Date>
  </mdb:dateInfo>
  <mdb:identificationInfo>
    <mri:MD_DataIdentification>
      <mri:citation>
        <cit:CI_Citation>
          <cit:date>
            <cit:CI_Date>
              <cit:date><gco:Date>2024-01-01</gco:Date></cit:date>
              <cit:dateType>
                <cit:CI_DateTypeCode codeList="x" codeListValue="creation"/>
              </cit:dateType>
            </cit:CI_Date>
          </cit:date>
        </cit:CI_Citation>
      </mri:citation>
    </mri:MD_DataIdentification>
  </mdb:identificationInfo>
</mdb:MD_Metadata>
"""

_SAMPLE_19115_3_WITH_REVISION = b"""\
<mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                 xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                 xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0"
                 xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0">
  <mdb:dateInfo>
    <cit:CI_Date>
      <cit:date><gco:DateTime>2024-01-01T00:00:00</gco:DateTime></cit:date>
      <cit:dateType>
        <cit:CI_DateTypeCode codeList="x" codeListValue="creation"/>
      </cit:dateType>
    </cit:CI_Date>
  </mdb:dateInfo>
  <mdb:dateInfo>
    <cit:CI_Date>
      <cit:date><gco:DateTime>2024-06-01T10:00:00</gco:DateTime></cit:date>
      <cit:dateType>
        <cit:CI_DateTypeCode codeList="x" codeListValue="revision"/>
      </cit:dateType>
    </cit:CI_Date>
  </mdb:dateInfo>
  <mdb:identificationInfo>
    <mri:MD_DataIdentification>
      <mri:citation>
        <cit:CI_Citation>
          <cit:date>
            <cit:CI_Date>
              <cit:date><gco:Date>2024-01-01</gco:Date></cit:date>
              <cit:dateType>
                <cit:CI_DateTypeCode codeList="x" codeListValue="creation"/>
              </cit:dateType>
            </cit:CI_Date>
          </cit:date>
          <cit:date>
            <cit:CI_Date>
              <cit:date><gco:Date>2024-06-01</gco:Date></cit:date>
              <cit:dateType>
                <cit:CI_DateTypeCode codeList="x" codeListValue="revision"/>
              </cit:dateType>
            </cit:CI_Date>
          </cit:date>
        </cit:CI_Citation>
      </mri:citation>
    </mri:MD_DataIdentification>
  </mdb:identificationInfo>
</mdb:MD_Metadata>
"""

_SAMPLE_19139_NO_REVISION = b"""\
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                 xmlns:gco="http://www.isotc211.org/2005/gco">
  <gmd:identificationInfo>
    <gmd:MD_DataIdentification>
      <gmd:citation>
        <gmd:CI_Citation>
          <gmd:date>
            <gmd:CI_Date>
              <gmd:date><gco:Date>2024-01-01</gco:Date></gmd:date>
              <gmd:dateType>
                <gmd:CI_DateTypeCode codeList="x" codeListValue="creation"/>
              </gmd:dateType>
            </gmd:CI_Date>
          </gmd:date>
        </gmd:CI_Citation>
      </gmd:citation>
    </gmd:MD_DataIdentification>
  </gmd:identificationInfo>
</gmd:MD_Metadata>
"""

_SAMPLE_19139_WITH_REVISION = b"""\
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                 xmlns:gco="http://www.isotc211.org/2005/gco">
  <gmd:identificationInfo>
    <gmd:MD_DataIdentification>
      <gmd:citation>
        <gmd:CI_Citation>
          <gmd:date>
            <gmd:CI_Date>
              <gmd:date><gco:Date>2024-01-01</gco:Date></gmd:date>
              <gmd:dateType>
                <gmd:CI_DateTypeCode codeList="x" codeListValue="creation"/>
              </gmd:dateType>
            </gmd:CI_Date>
          </gmd:date>
          <gmd:date>
            <gmd:CI_Date>
              <gmd:date><gco:Date>2024-06-01</gco:Date></gmd:date>
              <gmd:dateType>
                <gmd:CI_DateTypeCode codeList="x" codeListValue="revision"/>
              </gmd:dateType>
            </gmd:CI_Date>
          </gmd:date>
        </gmd:CI_Citation>
      </gmd:citation>
    </gmd:MD_DataIdentification>
  </gmd:identificationInfo>
</gmd:MD_Metadata>
"""

_SAMPLE_19115_3_WITH_REVISION_DATETIME = b"""\
<mdb:MD_Metadata xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/2.0"
                 xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/2.0"
                 xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0"
                 xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0">
  <mdb:identificationInfo>
    <mri:MD_DataIdentification>
      <mri:citation>
        <cit:CI_Citation>
          <cit:date>
            <cit:CI_Date>
              <cit:date><gco:DateTime>2024-06-01T10:00:00</gco:DateTime></cit:date>
              <cit:dateType>
                <cit:CI_DateTypeCode codeList="x" codeListValue="revision"/>
              </cit:dateType>
            </cit:CI_Date>
          </cit:date>
        </cit:CI_Citation>
      </mri:citation>
    </mri:MD_DataIdentification>
  </mdb:identificationInfo>
</mdb:MD_Metadata>
"""

_SAMPLE_19139_WITH_REVISION_DATETIME = b"""\
<gmd:MD_Metadata xmlns:gmd="http://www.isotc211.org/2005/gmd"
                 xmlns:gco="http://www.isotc211.org/2005/gco">
  <gmd:identificationInfo>
    <gmd:MD_DataIdentification>
      <gmd:citation>
        <gmd:CI_Citation>
          <gmd:date>
            <gmd:CI_Date>
              <gmd:date><gco:DateTime>2024-06-01T10:00:00</gco:DateTime></gmd:date>
              <gmd:dateType>
                <gmd:CI_DateTypeCode codeList="x" codeListValue="revision"/>
              </gmd:dateType>
            </gmd:CI_Date>
          </gmd:date>
        </gmd:CI_Citation>
      </gmd:citation>
    </gmd:MD_DataIdentification>
  </gmd:identificationInfo>
</gmd:MD_Metadata>
"""


class TestDetectSchema:
    def test_detects_19115_3(self) -> None:
        root = etree.fromstring(_SAMPLE_19115_3_NO_REVISION)
        assert MetadataService._detect_schema(root) == "19115-3"  # pyright: ignore[reportPrivateUsage]

    def test_detects_19139(self) -> None:
        root = etree.fromstring(_SAMPLE_19139_NO_REVISION)
        assert MetadataService._detect_schema(root) == "19139"  # pyright: ignore[reportPrivateUsage]

    def test_returns_none_for_unsupported(self) -> None:
        root = etree.fromstring(b"<root/>")
        assert MetadataService._detect_schema(root) is None  # pyright: ignore[reportPrivateUsage]


_CITATION_REVISION_XPATH_191153 = (
    "mdb:identificationInfo/mri:MD_DataIdentification"
    "/mri:citation/cit:CI_Citation"
    "/cit:date/cit:CI_Date[cit:dateType/cit:CI_DateTypeCode"
    "/@codeListValue='revision']/cit:date/gco:DateTime"
)


class TestUpdateRevisionDate191153:
    """Tests for _update_revision_date_19115_3."""

    def test_insert_when_absent(self) -> None:
        root = etree.fromstring(_SAMPLE_19115_3_NO_REVISION)
        rev_date = datetime(2025, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19115_3(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        # citation-level data revision date is inserted as gco:DateTime
        dt_nodes = root.xpath(_CITATION_REVISION_XPATH_191153, namespaces=NS_19115_3)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-03-15T14:30:00"

        # metadata-level mdb:dateInfo is NOT modified
        assert (
            len(
                root.xpath(
                    "mdb:dateInfo/cit:CI_Date[cit:dateType/cit:CI_DateTypeCode"
                    "/@codeListValue='revision']",
                    namespaces=NS_19115_3,
                )
            )
            == 0
        )

    def test_replace_gco_date_with_datetime(self) -> None:
        """Existing gco:Date revision is replaced with gco:DateTime."""
        root = etree.fromstring(_SAMPLE_19115_3_WITH_REVISION)
        rev_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19115_3(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(_CITATION_REVISION_XPATH_191153, namespaces=NS_19115_3)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-12-31T23:59:59"

        # metadata-level mdb:dateInfo[revision] is NOT modified
        mdb_nodes = root.xpath(
            "mdb:dateInfo/cit:CI_Date[cit:dateType/cit:CI_DateTypeCode"
            "/@codeListValue='revision']/cit:date/gco:DateTime",
            namespaces=NS_19115_3,
        )
        assert len(mdb_nodes) == 1
        assert mdb_nodes[0].text == "2024-06-01T10:00:00"

    def test_replace_existing_datetime(self) -> None:
        """Existing gco:DateTime revision is updated in place."""
        root = etree.fromstring(_SAMPLE_19115_3_WITH_REVISION_DATETIME)
        rev_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19115_3(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(_CITATION_REVISION_XPATH_191153, namespaces=NS_19115_3)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-12-31T23:59:59"


_CITATION_REVISION_XPATH_19139 = (
    "gmd:identificationInfo/gmd:MD_DataIdentification"
    "/gmd:citation/gmd:CI_Citation"
    "/gmd:date/gmd:CI_Date[gmd:dateType/gmd:CI_DateTypeCode"
    "/@codeListValue='revision']/gmd:date/gco:DateTime"
)


class TestUpdateRevisionDate19139:
    """Tests for _update_revision_date_19139."""

    def test_insert_when_absent(self) -> None:
        root = etree.fromstring(_SAMPLE_19139_NO_REVISION)
        rev_date = datetime(2025, 3, 15, 14, 30, 0, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19139(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(_CITATION_REVISION_XPATH_19139, namespaces=NS_19139)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-03-15T14:30:00"

    def test_replace_gco_date_with_datetime(self) -> None:
        """Existing gco:Date revision is replaced with gco:DateTime."""
        root = etree.fromstring(_SAMPLE_19139_WITH_REVISION)
        rev_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19139(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(_CITATION_REVISION_XPATH_19139, namespaces=NS_19139)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-12-31T23:59:59"

    def test_replace_existing_datetime(self) -> None:
        """Existing gco:DateTime revision is updated in place."""
        root = etree.fromstring(_SAMPLE_19139_WITH_REVISION_DATETIME)
        rev_date = datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        MetadataService._update_revision_date_19139(root, rev_date)  # pyright: ignore[reportPrivateUsage]

        dt_nodes = root.xpath(_CITATION_REVISION_XPATH_19139, namespaces=NS_19139)
        assert len(dt_nodes) == 1
        assert dt_nodes[0].text == "2025-12-31T23:59:59"


class TestUpdateRevisionDateEndToEnd:
    """Test update_revision_date() with mocked GeoNetwork calls."""

    @patch("src.services.metadata_service.GnApi")
    def test_fetch_update_save_19115_3(self, mock_gn_api: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.api_url = "http://test/api"
        mock_api.get_metadataxml.return_value = _SAMPLE_19115_3_NO_REVISION

        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_session.put.return_value = mock_resp
        mock_api.session = mock_session

        mock_gn_api.return_value = mock_api

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test")
        service.update_revision_date(
            "uuid-123", datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        )

        mock_api.get_metadataxml.assert_called_once_with("uuid-123")
        mock_session.put.assert_called_once()

        call_args = mock_session.put.call_args
        assert "uuid-123" in call_args[0][0]
        assert call_args[1]["headers"]["Content-Type"] == "application/xml"

        # Verify the saved XML contains the citation-level data revision date as gco:DateTime
        saved_xml = call_args[1]["data"]
        root = etree.fromstring(saved_xml)
        dt_nodes = root.xpath(_CITATION_REVISION_XPATH_191153, namespaces=NS_19115_3)
        assert dt_nodes[0].text == "2025-06-01T12:00:00"

    @patch("src.services.metadata_service.GnApi")
    def test_unsupported_schema_skips(self, mock_gn_api: MagicMock) -> None:
        mock_api = MagicMock()
        mock_api.api_url = "http://test/api"
        mock_api.get_metadataxml.return_value = b"<unknown/>"
        mock_api.session = MagicMock()
        mock_gn_api.return_value = mock_api

        service = MetadataService(gn_api_url="http://test/api", datadir_path="/test")
        service.update_revision_date("uuid-999", datetime.now(timezone.utc))

        mock_api.session.put.assert_not_called()


class TestGenerateMetadataCreationDate:
    """Verify creation date is set correctly and no revision date is present."""

    @patch("src.services.metadata_service.GnApi")
    def test_creation_date_in_generated_metadata(self, mock_gn_api: MagicMock) -> None:
        datadir = Path(__file__).resolve().parents[4] / "docker" / "datadir"

        service = MetadataService(
            gn_api_url="http://test/api",
            datadir_path=str(datadir),
        )

        link = IntegrityLink(
            id=uuid4(),
            integrity_title="Test",
            integrity_owner="user",
            integrity_organization="Org",
            staging_table_name="stg",
            created_at=datetime(2025, 3, 20, 10, 30, 0, tzinfo=timezone.utc),
            last_retrieval_timestamp=datetime(2025, 3, 20, 11, 0, 0, tzinfo=timezone.utc),
            source_import_type=ImportType.URL,
        )

        xml_str = service.generate_metadata(link)
        root = etree.fromstring(xml_str.encode())

        # mdb:dateInfo creation should have the real date
        creation_nodes = root.xpath(
            "mdb:dateInfo/cit:CI_Date[cit:dateType/cit:CI_DateTypeCode"
            "/@codeListValue='creation']/cit:date/gco:DateTime",
            namespaces=NS_19115_3,
        )
        assert len(creation_nodes) == 1
        assert creation_nodes[0].text == "2025-03-20T10:30:00"

        # No revision mdb:dateInfo should exist
        revision_nodes = root.xpath(
            "mdb:dateInfo/cit:CI_Date[cit:dateType/cit:CI_DateTypeCode/@codeListValue='revision']",
            namespaces=NS_19115_3,
        )
        assert len(revision_nodes) == 0
