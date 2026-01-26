"""Tests for integrity_links API routes."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.api.routes.ingestion.integrity_links import BATCH_SIZE, has_administrator_role
from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink


class TestHasAdministratorRole:
    """Test the has_administrator_role helper function."""

    def test_empty_roles_returns_false(self) -> None:
        """Test that empty roles string returns False."""
        assert has_administrator_role("") is False

    def test_none_like_roles_returns_false(self) -> None:
        """Test that whitespace-only roles return False."""
        assert has_administrator_role("   ") is False
        assert has_administrator_role(";") is False
        assert has_administrator_role(";;;") is False

    def test_administrator_role_found(self) -> None:
        """Test that ADMINISTRATOR role is detected."""
        assert has_administrator_role("ADMINISTRATOR") is True
        assert has_administrator_role("IMPORT;ADMINISTRATOR") is True
        assert has_administrator_role("ADMINISTRATOR;IMPORT;USER") is True

    def test_administrator_role_case_insensitive(self) -> None:
        """Test that role check is case-insensitive."""
        assert has_administrator_role("administrator") is True
        assert has_administrator_role("Administrator") is True
        assert has_administrator_role("IMPORT;administrator;USER") is True

    def test_administrator_role_with_whitespace(self) -> None:
        """Test that roles with extra whitespace are handled."""
        assert has_administrator_role(" ADMINISTRATOR ") is True
        assert has_administrator_role("IMPORT; ADMINISTRATOR ;USER") is True
        assert has_administrator_role("  IMPORT  ;  ADMINISTRATOR  ") is True

    def test_non_administrator_roles(self) -> None:
        """Test that non-administrator roles return False."""
        assert has_administrator_role("IMPORT") is False
        assert has_administrator_role("USER") is False
        assert has_administrator_role("IMPORT;USER;SUPERUSER") is False

    def test_partial_match_not_detected(self) -> None:
        """Test that partial matches are not detected as administrator."""
        assert has_administrator_role("ADMINISTRATORX") is False
        assert has_administrator_role("XADMINISTRATOR") is False
        assert has_administrator_role("SUPER_ADMINISTRATOR") is False


class TestListIntegrityLinks:
    """Test the list_integrity_links endpoint."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def sample_integrity_links(self) -> list[IntegrityLink]:
        """Create sample integrity links for testing."""
        links = []
        for i in range(5):
            # Create IntegrityLink without validation (direct instantiation)
            link = IntegrityLink(
                id=uuid4(),
                integrity_title=f"Test Link {i}",
                integrity_owner=f"user{i % 2}",  # Alternating users
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                source_url=f"http://example.com/{i}",
                source_auth_enabled=False,
                staging_table_name=f"staging_test_{i}",
                final_table_name=f"final_test_{i}" if i % 2 == 0 else None,
                created_at=datetime.now(timezone.utc),
                schedule_enabled=False,
            )
            links.append(link)
        return links

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_normal_user_sees_only_own_links(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        sample_integrity_links: list[IntegrityLink],
    ) -> None:
        """Test that normal users only see their own integrity links."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        # Filter links for user0
        user0_links = [link for link in sample_integrity_links if link.integrity_owner == "user0"]

        # Mock the session.exec().all() to return user0's links
        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = user0_links
        mock_session.exec.return_value = mock_exec_result

        response = list_integrity_links(
            session=mock_session,
            sec_username="user0",
            sec_roles="IMPORT;USER",
            offset=0,
        )

        assert len(response.items) == len(user0_links)
        for item in response.items:
            assert item.integrity_owner == "user0"

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_admin_sees_all_links(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        sample_integrity_links: list[IntegrityLink],
    ) -> None:
        """Test that administrators see all integrity links."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        # Mock the session.exec().all() to return all links
        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = sample_integrity_links
        mock_session.exec.return_value = mock_exec_result

        response = list_integrity_links(
            session=mock_session,
            sec_username="admin",
            sec_roles="IMPORT;ADMINISTRATOR;USER",
            offset=0,
        )

        assert len(response.items) == len(sample_integrity_links)

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_pagination_has_more_true(
        self, mock_logger: MagicMock, mock_session: MagicMock
    ) -> None:
        """Test that has_more is True when there are more items."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        # Create more than BATCH_SIZE links
        links = [
            IntegrityLink(
                id=uuid4(),
                integrity_title=f"Test Link {i}",
                integrity_owner="user0",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                source_auth_enabled=False,
                staging_table_name=f"staging_test_{i}",
                created_at=datetime.now(timezone.utc),
                schedule_enabled=False,
            )
            for i in range(BATCH_SIZE + 1)
        ]

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = links  # Returns BATCH_SIZE + 1 items
        mock_session.exec.return_value = mock_exec_result

        response = list_integrity_links(
            session=mock_session,
            sec_username="user0",
            sec_roles="IMPORT",
            offset=0,
        )

        assert response.has_more is True
        assert len(response.items) == BATCH_SIZE  # Only BATCH_SIZE items returned

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_pagination_has_more_false(
        self, mock_logger: MagicMock, mock_session: MagicMock
    ) -> None:
        """Test that has_more is False when there are no more items."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        # Create fewer than BATCH_SIZE links
        links = [
            IntegrityLink(
                id=uuid4(),
                integrity_title=f"Test Link {i}",
                integrity_owner="user0",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                source_auth_enabled=False,
                staging_table_name=f"staging_test_{i}",
                created_at=datetime.now(timezone.utc),
                schedule_enabled=False,
            )
            for i in range(10)
        ]

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = links
        mock_session.exec.return_value = mock_exec_result

        response = list_integrity_links(
            session=mock_session,
            sec_username="user0",
            sec_roles="IMPORT",
            offset=0,
        )

        assert response.has_more is False
        assert len(response.items) == 10

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_offset_parameter(self, mock_logger: MagicMock, mock_session: MagicMock) -> None:
        """Test that offset parameter is included in response."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = []
        mock_session.exec.return_value = mock_exec_result

        response = list_integrity_links(
            session=mock_session,
            sec_username="user0",
            sec_roles="IMPORT",
            offset=200,
        )

        assert response.offset == 200

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_sensitive_fields_excluded(
        self, mock_logger: MagicMock, mock_session: MagicMock
    ) -> None:
        """Test that sensitive fields are excluded from response."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        # Create link with sensitive data
        link = IntegrityLink(
            id=uuid4(),
            integrity_title="Test Link",
            integrity_owner="user0",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            source_username="secret_user",
            source_password_encrypted="encrypted_password",
            source_auth_enabled=True,
            staging_table_name="staging_test",
            staging_retrieve_time=None,
            integrity_transformation={"key": "value"},
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [link]
        mock_session.exec.return_value = mock_exec_result

        response = list_integrity_links(
            session=mock_session,
            sec_username="user0",
            sec_roles="IMPORT",
            offset=0,
        )

        assert len(response.items) == 1
        item = response.items[0]

        # Check that sensitive fields are not present in the response model
        item_dict = item.model_dump()
        assert "source_username" not in item_dict
        assert "source_password_encrypted" not in item_dict
        assert "integrity_transformation" not in item_dict
        assert "staging_retrieve_time" not in item_dict

        # Check that non-sensitive fields are present
        assert "id" in item_dict
        assert "integrity_title" in item_dict
        assert "integrity_owner" in item_dict

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_empty_result(self, mock_logger: MagicMock, mock_session: MagicMock) -> None:
        """Test handling of empty results."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = []
        mock_session.exec.return_value = mock_exec_result

        response = list_integrity_links(
            session=mock_session,
            sec_username="newuser",
            sec_roles="IMPORT",
            offset=0,
        )

        assert len(response.items) == 0
        assert response.has_more is False
        assert response.offset == 0

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_response_model_structure(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        sample_integrity_links: list[IntegrityLink],
    ) -> None:
        """Test that response model has correct structure."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = sample_integrity_links[:1]
        mock_session.exec.return_value = mock_exec_result

        response = list_integrity_links(
            session=mock_session,
            sec_username="user0",
            sec_roles="IMPORT",
            offset=0,
        )

        # Check response structure
        assert hasattr(response, "items")
        assert hasattr(response, "has_more")
        assert hasattr(response, "offset")

        # Check item structure
        item = response.items[0]
        assert hasattr(item, "id")
        assert hasattr(item, "integrity_title")
        assert hasattr(item, "integrity_owner")
        assert hasattr(item, "integrity_organization")
        assert hasattr(item, "source_import_type")
        assert hasattr(item, "source_file_name")
        assert hasattr(item, "source_file_type")
        assert hasattr(item, "source_url")
        assert hasattr(item, "source_auth_enabled")
        assert hasattr(item, "staging_table_name")
        assert hasattr(item, "final_table_name")
        assert hasattr(item, "metadata_id")
        assert hasattr(item, "data_id")
        assert hasattr(item, "created_at")
        assert hasattr(item, "last_retrieval_timestamp")
        assert hasattr(item, "schedule")
        assert hasattr(item, "schedule_enabled")
