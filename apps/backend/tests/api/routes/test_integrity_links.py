"""Tests for integrity_links API routes."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.api.routes.ingestion.integrity_links import BATCH_SIZE
from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.services.georchestra import GeorchestraContext


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

    def _create_geo_ctx(self, username: str, roles: set[str] | None = None) -> GeorchestraContext:
        """Create a GeorchestraContext for testing."""
        return GeorchestraContext(
            username=username,
            roles=roles or set(),
            email="",
            firstname="",
            lastname="",
        )

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

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT", "USER"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
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

        geo_ctx = self._create_geo_ctx("admin", {"IMPORT", "ADMINISTRATOR", "USER"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
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

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
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

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
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

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
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

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
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

        geo_ctx = self._create_geo_ctx("newuser", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
            offset=0,
        )

        assert len(response.items) == 0
        assert response.has_more is False
        assert response.offset == 0

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_search_parameter_filters_by_title(
        self, mock_logger: MagicMock, mock_session: MagicMock
    ) -> None:
        """Test that the search parameter filters results by integrity_title."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        matching_link = IntegrityLink(
            id=uuid4(),
            integrity_title="My Dataset Import",
            integrity_owner="user0",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            source_auth_enabled=False,
            staging_table_name="staging_test",
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [matching_link]
        mock_session.exec.return_value = mock_exec_result

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
            offset=0,
            search="Dataset",
        )

        assert len(response.items) == 1
        assert response.items[0].integrity_title == "My Dataset Import"

        # Verify the query passed to session.exec contains an ilike filter
        executed_query = mock_session.exec.call_args[0][0]
        query_str = str(executed_query)
        assert "ilike" in query_str.lower() or "LIKE" in query_str

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_search_with_pagination(self, mock_logger: MagicMock, mock_session: MagicMock) -> None:
        """Test that search works correctly with pagination."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        # Simulate BATCH_SIZE + 1 results (has_more = True)
        links = [
            IntegrityLink(
                id=uuid4(),
                integrity_title=f"Matching Link {i}",
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
        mock_exec_result.all.return_value = links
        mock_session.exec.return_value = mock_exec_result

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
            offset=50,
            search="Matching",
        )

        assert response.has_more is True
        assert len(response.items) == BATCH_SIZE
        assert response.offset == 50

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_search_empty_string_ignored(
        self, mock_logger: MagicMock, mock_session: MagicMock
    ) -> None:
        """Test that an empty search string does not add a filter."""
        from src.api.routes.ingestion.integrity_links import list_integrity_links

        links = [
            IntegrityLink(
                id=uuid4(),
                integrity_title="Any Link",
                integrity_owner="user0",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                source_auth_enabled=False,
                staging_table_name="staging_test",
                created_at=datetime.now(timezone.utc),
                schedule_enabled=False,
            )
        ]

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = links
        mock_session.exec.return_value = mock_exec_result

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        # Empty string should be treated as no filter
        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
            offset=0,
            search="",
        )

        assert len(response.items) == 1

        # Verify no ilike filter was added
        executed_query = mock_session.exec.call_args[0][0]
        query_str = str(executed_query)
        assert "ilike" not in query_str.lower() and "LIKE" not in query_str

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

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            geo_ctx=geo_ctx,
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
