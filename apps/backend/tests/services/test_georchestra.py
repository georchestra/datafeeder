"""Tests for geOrchestra security context service."""

from unittest.mock import MagicMock

import pytest

from src.services.georchestra import GeorchestraContext, get_georchestra_context


class TestGeorchestraContextHasRole:
    """Test the GeorchestraContext.has_role() method."""

    def test_has_role_returns_true_for_exact_match(self) -> None:
        """Test that has_role returns True for an exact role match."""
        ctx = GeorchestraContext(
            username="testuser",
            roles={"ADMIN", "USER"},
            email="",
            firstname="",
            lastname="",
            organization="",
        )
        assert ctx.has_role("ADMIN") is True
        assert ctx.has_role("USER") is True

    def test_has_role_is_case_insensitive(self) -> None:
        """Test that has_role comparison is case-insensitive."""
        ctx = GeorchestraContext(
            username="testuser",
            roles={"ADMINISTRATOR"},
            email="",
            firstname="",
            lastname="",
            organization="",
        )
        assert ctx.has_role("administrator") is True
        assert ctx.has_role("Administrator") is True
        assert ctx.has_role("ADMINISTRATOR") is True

    def test_has_role_returns_false_for_missing_role(self) -> None:
        """Test that has_role returns False when role is not present."""
        ctx = GeorchestraContext(
            username="testuser",
            roles={"USER", "IMPORT"},
            email="",
            firstname="",
            lastname="",
            organization="",
        )
        assert ctx.has_role("ADMIN") is False
        assert ctx.has_role("ADMINISTRATOR") is False

    def test_has_role_with_empty_roles(self) -> None:
        """Test has_role with empty roles set."""
        ctx = GeorchestraContext(
            username="testuser",
            roles=set(),
            email="",
            firstname="",
            lastname="",
            organization="",
        )
        assert ctx.has_role("ADMIN") is False


class TestGeorchestraContextIsAdministrator:
    """Test the GeorchestraContext.is_administrator() method."""

    def test_is_administrator_returns_true(self) -> None:
        """Test that is_administrator returns True for ADMINISTRATOR role."""
        ctx = GeorchestraContext(
            username="admin",
            roles={"ADMINISTRATOR"},
            email="",
            firstname="",
            lastname="",
            organization="",
        )
        assert ctx.is_administrator() is True

    def test_is_administrator_with_multiple_roles(self) -> None:
        """Test is_administrator with multiple roles including ADMINISTRATOR."""
        ctx = GeorchestraContext(
            username="admin",
            roles={"IMPORT", "ADMINISTRATOR", "USER"},
            email="",
            firstname="",
            lastname="",
            organization="",
        )
        assert ctx.is_administrator() is True

    def test_is_administrator_returns_false(self) -> None:
        """Test that is_administrator returns False when ADMINISTRATOR not present."""
        ctx = GeorchestraContext(
            username="user",
            roles={"IMPORT", "USER"},
            email="",
            firstname="",
            lastname="",
            organization="",
        )
        assert ctx.is_administrator() is False

    def test_is_administrator_with_empty_roles(self) -> None:
        """Test is_administrator with empty roles set."""
        ctx = GeorchestraContext(
            username="user",
            roles=set(),
            email="",
            firstname="",
            lastname="",
            organization="",
        )
        assert ctx.is_administrator() is False


class TestGetGeorchestraContext:
    """Test the get_georchestra_context() function."""

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock FastAPI Request object."""
        request = MagicMock()
        request.headers = {}
        return request

    def test_extracts_username_from_header(self, mock_request: MagicMock) -> None:
        """Test that username is extracted from sec-username header."""
        mock_request.headers = {"sec-username": "testuser"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.username == "testuser"

    def test_extracts_email_from_header(self, mock_request: MagicMock) -> None:
        """Test that email is extracted from sec-email header."""
        mock_request.headers = {"sec-email": "test@example.com"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.email == "test@example.com"

    def test_extracts_firstname_from_header(self, mock_request: MagicMock) -> None:
        """Test that firstname is extracted from sec-firstname header."""
        mock_request.headers = {"sec-firstname": "John"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.firstname == "John"

    def test_extracts_lastname_from_header(self, mock_request: MagicMock) -> None:
        """Test that lastname is extracted from sec-lastname header."""
        mock_request.headers = {"sec-lastname": "Doe"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.lastname == "Doe"

    def test_extracts_organization_from_header(self, mock_request: MagicMock) -> None:
        """Test that organization is extracted from sec-org header."""
        mock_request.headers = {"sec-org": "my_org"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.organization == "my_org"

    def test_extracts_all_fields(self, mock_request: MagicMock) -> None:
        """Test that all fields are extracted correctly."""
        mock_request.headers = {
            "sec-username": "jdoe",
            "sec-roles": "IMPORT;USER",
            "sec-email": "jdoe@example.com",
            "sec-firstname": "John",
            "sec-lastname": "Doe",
            "sec-org": "my_org",
        }

        ctx = get_georchestra_context(mock_request)

        assert ctx.username == "jdoe"
        assert ctx.roles == {"IMPORT", "USER"}
        assert ctx.email == "jdoe@example.com"
        assert ctx.firstname == "John"
        assert ctx.lastname == "Doe"
        assert ctx.organization == "my_org"

    def test_missing_headers_return_empty_strings(self, mock_request: MagicMock) -> None:
        """Test that missing headers result in empty strings."""
        mock_request.headers = {}

        ctx = get_georchestra_context(mock_request)

        assert ctx.username == ""
        assert ctx.email == ""
        assert ctx.firstname == ""
        assert ctx.lastname == ""
        assert ctx.organization == ""
        assert ctx.roles == set()


class TestRoleParsing:
    """Test role parsing in get_georchestra_context()."""

    @pytest.fixture
    def mock_request(self) -> MagicMock:
        """Create a mock FastAPI Request object."""
        request = MagicMock()
        request.headers = {}
        return request

    def test_parses_single_role(self, mock_request: MagicMock) -> None:
        """Test parsing a single role."""
        mock_request.headers = {"sec-roles": "ADMINISTRATOR"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.roles == {"ADMINISTRATOR"}

    def test_parses_multiple_semicolon_separated_roles(self, mock_request: MagicMock) -> None:
        """Test parsing multiple semicolon-separated roles."""
        mock_request.headers = {"sec-roles": "IMPORT;ADMINISTRATOR;USER"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.roles == {"IMPORT", "ADMINISTRATOR", "USER"}

    def test_normalizes_roles_to_uppercase(self, mock_request: MagicMock) -> None:
        """Test that roles are normalized to uppercase."""
        mock_request.headers = {"sec-roles": "administrator;Import;User"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.roles == {"ADMINISTRATOR", "IMPORT", "USER"}

    def test_handles_whitespace_in_roles(self, mock_request: MagicMock) -> None:
        """Test that whitespace around roles is trimmed."""
        mock_request.headers = {"sec-roles": " IMPORT ; ADMINISTRATOR ; USER "}

        ctx = get_georchestra_context(mock_request)

        assert ctx.roles == {"IMPORT", "ADMINISTRATOR", "USER"}

    def test_handles_empty_roles_string(self, mock_request: MagicMock) -> None:
        """Test parsing empty roles string."""
        mock_request.headers = {"sec-roles": ""}

        ctx = get_georchestra_context(mock_request)

        assert ctx.roles == set()

    def test_handles_only_semicolons(self, mock_request: MagicMock) -> None:
        """Test parsing roles string with only semicolons."""
        mock_request.headers = {"sec-roles": ";;;"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.roles == set()

    def test_handles_whitespace_only_roles(self, mock_request: MagicMock) -> None:
        """Test parsing roles string with only whitespace."""
        mock_request.headers = {"sec-roles": "   "}

        ctx = get_georchestra_context(mock_request)

        assert ctx.roles == set()

    def test_handles_mixed_empty_and_valid_roles(self, mock_request: MagicMock) -> None:
        """Test parsing roles with some empty entries."""
        mock_request.headers = {"sec-roles": "IMPORT;;USER;  ;ADMIN"}

        ctx = get_georchestra_context(mock_request)

        assert ctx.roles == {"IMPORT", "USER", "ADMIN"}
