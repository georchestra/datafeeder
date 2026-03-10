"""Tests for integrity_links API routes."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from src.api.routes.ingestion.integrity_links import BATCH_SIZE, list_integrity_links
from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.services.georchestra import GeorchestraContext


class TestListIntegrityLinks:
    """Test the list_integrity_links endpoint."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock datafeeder database session."""
        return MagicMock()

    @pytest.fixture
    def mock_data_session(self) -> MagicMock:
        """Create a mock data engine session for table existence checks."""
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
                staging_table_name=f"staging_test_{i}",
                final_table_name=f"final_test_{i}" if i % 2 == 0 else None,
                created_at=datetime.now(timezone.utc),
                schedule_enabled=False,
            )
            links.append(link)
        return links

    def _create_geo_ctx(
        self, username: str, roles: set[str] | None = None, organization: str = ""
    ) -> GeorchestraContext:
        """Create a GeorchestraContext for testing."""
        return GeorchestraContext(
            username=username,
            roles=roles or set(),
            email="",
            firstname="",
            lastname="",
            organization=organization,
        )

    def _setup_session(self, mock_session: MagicMock, links: list[IntegrityLink]) -> None:
        """Set up datafeeder session mock to return (link, access_level) 2-tuples via .all()."""
        mock_exec = MagicMock()
        mock_exec.all.return_value = [(link, "OWNER") for link in links]
        mock_session.execute.return_value = mock_exec

    def _setup_data_session(
        self,
        mock_data_session: MagicMock,
        staging_names: list[str],
        final_names: list[str] = [],
    ) -> None:
        """Set up data_session mock to return table names for staging then final queries."""
        mock_staging = MagicMock()
        mock_staging.scalars.return_value.all.return_value = staging_names
        mock_final = MagicMock()
        mock_final.scalars.return_value.all.return_value = final_names
        mock_data_session.execute.side_effect = [mock_staging, mock_final]

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_normal_user_sees_only_own_links(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        mock_data_session: MagicMock,
        sample_integrity_links: list[IntegrityLink],
    ) -> None:
        """Test that normal users only see their own integrity links."""

        # Filter links for user0
        user0_links = [link for link in sample_integrity_links if link.integrity_owner == "user0"]
        self._setup_session(mock_session, user0_links)
        staging = [lnk.staging_table_name for lnk in user0_links if lnk.staging_table_name]
        final = [lnk.final_table_name for lnk in user0_links if lnk.final_table_name]
        self._setup_data_session(mock_data_session, staging, final)

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT", "USER"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
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
        mock_data_session: MagicMock,
        sample_integrity_links: list[IntegrityLink],
    ) -> None:
        """Test that administrators see all integrity links."""

        self._setup_session(mock_session, sample_integrity_links)
        staging = [
            lnk.staging_table_name for lnk in sample_integrity_links if lnk.staging_table_name
        ]
        final = [lnk.final_table_name for lnk in sample_integrity_links if lnk.final_table_name]
        self._setup_data_session(mock_data_session, staging, final)

        geo_ctx = self._create_geo_ctx("admin", {"IMPORT", "ADMINISTRATOR", "USER"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert len(response.items) == len(sample_integrity_links)

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_pagination_has_more_true(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Test that has_more is True when there are more items."""

        # Create more than BATCH_SIZE links, all with staging tables
        links = [
            IntegrityLink(
                id=uuid4(),
                integrity_title=f"Test Link {i}",
                integrity_owner="user0",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                staging_table_name=f"staging_test_{i}",
                created_at=datetime.now(timezone.utc),
                schedule_enabled=False,
            )
            for i in range(BATCH_SIZE + 1)
        ]

        self._setup_session(mock_session, links)
        staging = [lnk.staging_table_name for lnk in links if lnk.staging_table_name]
        self._setup_data_session(mock_data_session, staging, [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert response.has_more is True
        assert len(response.items) == BATCH_SIZE  # Only BATCH_SIZE items returned

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_pagination_has_more_false(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Test that has_more is False when there are no more items."""

        # Create fewer than BATCH_SIZE links
        links = [
            IntegrityLink(
                id=uuid4(),
                integrity_title=f"Test Link {i}",
                integrity_owner="user0",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                staging_table_name=f"staging_test_{i}",
                created_at=datetime.now(timezone.utc),
                schedule_enabled=False,
            )
            for i in range(10)
        ]

        self._setup_session(mock_session, links)
        staging = [lnk.staging_table_name for lnk in links if lnk.staging_table_name]
        self._setup_data_session(mock_data_session, staging, [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert response.has_more is False
        assert len(response.items) == 10

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_offset_parameter(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Test that offset parameter is included in response."""

        self._setup_session(mock_session, [])
        self._setup_data_session(mock_data_session, [], [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=200,
        )

        assert response.offset == 200

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_sensitive_fields_excluded(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Test that sensitive fields are excluded from response."""

        # Create link with sensitive data
        link = IntegrityLink(
            id=uuid4(),
            integrity_title="Test Link",
            integrity_owner="user0",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            source_username="secret_user",
            source_password_encrypted="encrypted_password",
            staging_table_name="staging_test",
            staging_retrieve_time=None,
            integrity_transformation={"key": "value"},
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

        self._setup_session(mock_session, [link])
        self._setup_data_session(mock_data_session, ["staging_test"], [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
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
    def test_empty_result(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Test handling of empty results."""

        self._setup_session(mock_session, [])
        self._setup_data_session(mock_data_session, [], [])

        geo_ctx = self._create_geo_ctx("newuser", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert len(response.items) == 0
        assert response.has_more is False
        assert response.offset == 0

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_search_parameter_filters_by_title(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Test that the search parameter filters results by integrity_title."""

        matching_link = IntegrityLink(
            id=uuid4(),
            integrity_title="My Dataset Import",
            integrity_owner="user0",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

        self._setup_session(mock_session, [matching_link])
        self._setup_data_session(mock_data_session, ["staging_test"], [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
            search="Dataset",
        )

        assert len(response.items) == 1
        assert response.items[0].integrity_title == "My Dataset Import"

        # Verify the query passed to session.execute contains an ilike filter
        executed_query = mock_session.execute.call_args[0][0]
        query_str = str(executed_query)
        assert "ilike" in query_str.lower() or "LIKE" in query_str

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_search_with_pagination(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Test that search works correctly with pagination."""

        # Simulate BATCH_SIZE + 1 results (has_more = True)
        links = [
            IntegrityLink(
                id=uuid4(),
                integrity_title=f"Matching Link {i}",
                integrity_owner="user0",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                staging_table_name=f"staging_test_{i}",
                created_at=datetime.now(timezone.utc),
                schedule_enabled=False,
            )
            for i in range(BATCH_SIZE + 1)
        ]

        self._setup_session(mock_session, links)
        staging = [lnk.staging_table_name for lnk in links if lnk.staging_table_name]
        self._setup_data_session(mock_data_session, staging, [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=50,
            search="Matching",
        )

        assert response.has_more is True
        assert len(response.items) == BATCH_SIZE
        assert response.offset == 50

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_search_empty_string_ignored(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Test that an empty search string does not add a filter."""

        links = [
            IntegrityLink(
                id=uuid4(),
                integrity_title="Any Link",
                integrity_owner="user0",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                staging_table_name="staging_test",
                created_at=datetime.now(timezone.utc),
                schedule_enabled=False,
            )
        ]

        self._setup_session(mock_session, links)
        self._setup_data_session(mock_data_session, ["staging_test"], [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        # Empty string should be treated as no filter
        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
            search="",
        )

        assert len(response.items) == 1

        # Verify no ilike filter was added
        executed_query = mock_session.execute.call_args[0][0]
        query_str = str(executed_query)
        assert "ilike" not in query_str.lower() and "LIKE" not in query_str

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_response_model_structure(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        mock_data_session: MagicMock,
        sample_integrity_links: list[IntegrityLink],
    ) -> None:
        """Test that response model has correct structure."""

        # sample_integrity_links[0]: staging_table_name="staging_test_0", final_table_name="final_test_0"
        link = sample_integrity_links[0]
        self._setup_session(mock_session, [link])
        self._setup_data_session(
            mock_data_session,
            [link.staging_table_name] if link.staging_table_name else [],
            [link.final_table_name] if link.final_table_name else [],
        )

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
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
        assert hasattr(item, "staging_table_name")
        assert hasattr(item, "final_table_name")
        assert hasattr(item, "metadata_id")
        assert hasattr(item, "data_id")
        assert hasattr(item, "created_at")
        assert hasattr(item, "last_retrieval_timestamp")
        assert hasattr(item, "schedule")
        assert hasattr(item, "schedule_enabled")
        assert hasattr(item, "access_level")
        assert hasattr(item, "has_final_table")
        assert item.has_final_table is True  # final_test_0 is in final_tables

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_has_final_table_false_when_no_final_table(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Test that has_final_table is False when the final table does not exist."""
        link = IntegrityLink(
            id=uuid4(),
            integrity_title="No Final Table",
            integrity_owner="user0",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

        self._setup_session(mock_session, [link])
        self._setup_data_session(mock_data_session, ["staging_test"], [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert len(response.items) == 1
        assert response.items[0].has_final_table is False

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_link_excluded_when_staging_table_not_in_db(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Links whose staging table no longer exists in the DB are filtered out."""
        link = IntegrityLink(
            id=uuid4(),
            integrity_title="Orphaned Link",
            integrity_owner="user0",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_dropped",
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

        self._setup_session(mock_session, [link])
        # DB returns nothing for the candidate — table has been dropped.
        self._setup_data_session(mock_data_session, [], [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert len(response.items) == 0

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_link_included_via_final_table_only(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """A link whose staging table is absent from DB is still included when its final table exists."""
        link = IntegrityLink(
            id=uuid4(),
            integrity_title="Final Fallback",
            integrity_owner="user0",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_not_in_db",
            final_table_name="final_only_table",
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

        self._setup_session(mock_session, [link])
        # staging query returns nothing; final query returns the table
        self._setup_data_session(mock_data_session, [], ["final_only_table"])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert len(response.items) == 1
        assert response.items[0].has_final_table is True

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_link_with_both_tables_only_staging_exists(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """A link with both table names is included but has_final_table=False when only staging exists."""
        link = IntegrityLink(
            id=uuid4(),
            integrity_title="Partial Tables",
            integrity_owner="user0",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_exists",
            final_table_name="final_missing",
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

        self._setup_session(mock_session, [link])
        # staging exists, final does not
        self._setup_data_session(mock_data_session, ["staging_exists"], [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert len(response.items) == 1
        assert response.items[0].has_final_table is False

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_no_db_query_when_no_links(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """data_session.execute is never called when the page of links is empty."""
        self._setup_session(mock_session, [])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert len(response.items) == 0
        # No links → no candidates → neither staging nor final query is fired
        mock_data_session.execute.assert_not_called()

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_only_candidate_names_passed_to_db_query(
        self, mock_logger: MagicMock, mock_session: MagicMock, mock_data_session: MagicMock
    ) -> None:
        """Only the table names from the fetched links are passed to the IN clause."""
        link = IntegrityLink(
            id=uuid4(),
            integrity_title="Scoped Query",
            integrity_owner="user0",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="my_staging_table",
            final_table_name="my_final_table",
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

        self._setup_session(mock_session, [link])
        self._setup_data_session(mock_data_session, ["my_staging_table"], ["my_final_table"])

        geo_ctx = self._create_geo_ctx("user0", {"IMPORT"})

        list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=geo_ctx,
            org_id=None,
            offset=0,
        )

        assert mock_data_session.execute.call_count == 2

        staging_query = mock_data_session.execute.call_args_list[0][0][0]
        final_query = mock_data_session.execute.call_args_list[1][0][0]

        # Use literal_binds to render actual IN values into the SQL string
        staging_sql = str(staging_query.compile(compile_kwargs={"literal_binds": True}))
        final_sql = str(final_query.compile(compile_kwargs={"literal_binds": True}))

        assert "my_staging_table" in staging_sql
        assert "my_final_table" in final_sql


class TestListIntegrityLinksVisibility:
    """Test dataset list visibility based on permissions (task 3.3)."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_data_session(self) -> MagicMock:
        """Create a mock data engine session."""
        return MagicMock()

    def _make_link(self, owner: str = "other_user", org: str = "other_org") -> IntegrityLink:
        """Create a sample IntegrityLink."""
        return IntegrityLink(
            id=uuid4(),
            integrity_title="Test Link",
            integrity_owner=owner,
            integrity_organization=org,
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            created_at=datetime.now(timezone.utc),
            schedule_enabled=False,
        )

    def _geo_ctx(
        self,
        username: str = "user1",
        organization: str = "org_a",
        is_admin: bool = False,
    ) -> GeorchestraContext:
        roles = {"ADMINISTRATOR"} if is_admin else {"IMPORT"}
        return GeorchestraContext(
            username=username,
            roles=roles,
            email="",
            firstname="",
            lastname="",
            organization=organization,
        )

    def _setup_data_session(
        self, mock_data_session: MagicMock, staging_names: list[str], final_names: list[str] = []
    ) -> None:
        """Set up data_session mock to return table names for staging then final queries."""
        mock_staging = MagicMock()
        mock_staging.scalars.return_value.all.return_value = staging_names
        mock_final = MagicMock()
        mock_final.scalars.return_value.all.return_value = final_names
        mock_data_session.execute.side_effect = [mock_staging, mock_final]

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_owner_sees_own_datasets_with_owner_access_level(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        mock_data_session: MagicMock,
    ) -> None:
        """Owner sees own datasets and gets OWNER access level."""

        link = self._make_link(owner="user1")
        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [(link, "OWNER")]
        mock_session.execute.return_value = mock_exec_result
        staging = [link.staging_table_name] if link.staging_table_name else []
        self._setup_data_session(mock_data_session, staging)

        ctx = self._geo_ctx(username="user1")
        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=ctx,
            org_id="org-uuid",
            offset=0,
        )

        assert len(response.items) == 1
        assert response.items[0].access_level == "OWNER"

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_admin_sees_all_with_admin_access_level(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        mock_data_session: MagicMock,
    ) -> None:
        """Admin sees all datasets and gets ADMIN access level."""

        links = [self._make_link(owner="someone"), self._make_link(owner="another")]
        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [(link, "ADMIN") for link in links]
        mock_session.execute.return_value = mock_exec_result
        self._setup_data_session(mock_data_session, ["staging_test"])

        ctx = self._geo_ctx(is_admin=True)
        response = list_integrity_links(
            session=mock_session, data_session=mock_data_session, geo_ctx=ctx, org_id=None, offset=0
        )

        assert len(response.items) == 2
        for item in response.items:
            assert item.access_level == "ADMIN"

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_group_with_metadata_read_gets_read_access_level(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        mock_data_session: MagicMock,
    ) -> None:
        """User whose group has METADATA READ sees dataset with READ access level."""

        link = self._make_link(owner="other")
        org_id = "test-org-uuid"

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [(link, "READ")]
        mock_session.execute.return_value = mock_exec_result
        staging = [link.staging_table_name] if link.staging_table_name else []
        self._setup_data_session(mock_data_session, staging)

        ctx = self._geo_ctx(username="user1", organization="org_a")
        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=ctx,
            org_id=org_id,
            offset=0,
        )

        assert len(response.items) == 1
        assert response.items[0].access_level == "READ"

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_group_with_metadata_write_gets_write_access_level(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        mock_data_session: MagicMock,
    ) -> None:
        """User whose group has METADATA WRITE sees dataset with WRITE access level."""

        link = self._make_link(owner="other")
        org_id = "test-org-uuid"

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = [(link, "WRITE")]
        mock_session.execute.return_value = mock_exec_result
        staging = [link.staging_table_name] if link.staging_table_name else []
        self._setup_data_session(mock_data_session, staging)

        ctx = self._geo_ctx(username="user1", organization="org_a")
        response = list_integrity_links(
            session=mock_session,
            data_session=mock_data_session,
            geo_ctx=ctx,
            org_id=org_id,
            offset=0,
        )

        assert len(response.items) == 1
        assert response.items[0].access_level == "WRITE"

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_no_permission_user_sees_empty_list(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        mock_data_session: MagicMock,
    ) -> None:
        """User with no ownership and no group rules sees empty list."""

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = []
        mock_session.execute.return_value = mock_exec_result
        self._setup_data_session(mock_data_session, [])

        ctx = self._geo_ctx(username="nobody", organization="no_org")
        response = list_integrity_links(
            session=mock_session, data_session=mock_data_session, geo_ctx=ctx, org_id=None, offset=0
        )

        assert len(response.items) == 0

    @patch("src.api.routes.ingestion.integrity_links.logger")
    def test_query_includes_or_condition_for_non_admin(
        self,
        mock_logger: MagicMock,
        mock_session: MagicMock,
        mock_data_session: MagicMock,
    ) -> None:
        """Non-admin query should include OR condition for ownership + org rules."""

        mock_exec_result = MagicMock()
        mock_exec_result.all.return_value = []
        mock_session.execute.return_value = mock_exec_result
        self._setup_data_session(mock_data_session, [])

        ctx = self._geo_ctx(username="user1", organization="org_a")
        list_integrity_links(
            session=mock_session, data_session=mock_data_session, geo_ctx=ctx, org_id=None, offset=0
        )

        # Verify the query was executed and contains both conditions
        executed_query = mock_session.execute.call_args[0][0]
        query_str = str(executed_query)
        # Should have OR condition (owner = username OR EXISTS subquery)
        assert "OR" in query_str.upper() or "or" in query_str.lower()
