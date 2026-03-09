"""Tests for permission-checking dependency in core/security.py."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest
from fastapi import HTTPException

from src.api.deps import get_org_id
from src.core.security import (
    AccessLevel,
    EffectiveAccess,
    compute_effective_access,
    load_authorized_integrity_link,
)
from src.models.integrity_link import IntegrityLink
from src.services.georchestra import GeorchestraContext

DATASET_ID = "11111111-1111-1111-1111-111111111111"
DATASET_UUID = UUID(DATASET_ID)

# A non-None org UUID used by group-access tests (value is arbitrary—the session mock
# ignores query parameters).
ORG_UUID = "aaaabbbb-cccc-dddd-eeee-ffffffffffff"


def _geo_ctx(
    username: str = "user1",
    organization: str = "org_a",
    is_admin: bool = False,
) -> GeorchestraContext:
    """Create a test GeorchestraContext."""
    roles = {"ADMINISTRATOR"} if is_admin else {"IMPORT"}
    return GeorchestraContext(
        username=username,
        roles=roles,
        email="",
        firstname="",
        lastname="",
        organization=organization,
    )


def _integrity_link(owner: str = "owner1") -> IntegrityLink:
    """Create a test IntegrityLink."""
    link = MagicMock(spec=IntegrityLink)
    link.id = DATASET_UUID
    link.integrity_owner = owner
    return link


def _mock_session(
    integrity_link: IntegrityLink | None = None,
    access_result: str | None = "__unset__",
) -> MagicMock:
    """Create a mock session with configurable query results.

    Args:
        integrity_link: Value returned by ``session.get()`` (for
            load_authorized_integrity_link).
        access_result: Value returned by ``session.exec().first()`` —
            simulates the SQL access_level expression result used by
            ``compute_effective_access``.  Pass ``"__unset__"`` (default)
            to leave ``.first()`` as a generic Mock.
    """
    session = MagicMock()
    if integrity_link is not None:
        session.get.return_value = integrity_link
    mock_exec = MagicMock()
    if access_result != "__unset__":
        mock_exec.first.return_value = access_result
    session.exec.return_value = mock_exec
    return session


# ────────────────────────────────────────────────────────
# compute_effective_access
# ────────────────────────────────────────────────────────


class TestComputeEffectiveAccessAdmin:
    """Admin always gets ADMIN access."""

    def test_admin_gets_admin_access(self) -> None:
        link = _integrity_link(owner="someone_else")
        ctx = _geo_ctx(is_admin=True)
        session = _mock_session(access_result="ADMIN")

        result = compute_effective_access(link, ctx, session, None)

        assert result == EffectiveAccess.ADMIN

    def test_admin_skips_rule_query(self) -> None:
        """Admin path still executes one query (for the SQL expression)."""
        link = _integrity_link()
        ctx = _geo_ctx(is_admin=True)
        session = _mock_session(access_result="ADMIN")

        compute_effective_access(link, ctx, session, None)

        session.exec.assert_called_once()


class TestComputeEffectiveAccessOwner:
    """Owner always gets OWNER access."""

    def test_owner_gets_owner_access(self) -> None:
        link = _integrity_link(owner="user1")
        ctx = _geo_ctx(username="user1")
        session = _mock_session(access_result="OWNER")

        result = compute_effective_access(link, ctx, session, None)

        assert result == EffectiveAccess.OWNER

    def test_owner_executes_one_query(self) -> None:
        """Owner path executes one query (for the SQL expression)."""
        link = _integrity_link(owner="user1")
        ctx = _geo_ctx(username="user1")
        session = _mock_session(access_result="OWNER")

        compute_effective_access(link, ctx, session, None)

        session.exec.assert_called_once()


class TestComputeEffectiveAccessGroupRules:
    """Group-based access through IntegrityLinkRule matching."""

    def test_write_rule_gives_write_access(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx(username="user1", organization="org_a")
        session = _mock_session(access_result="WRITE")

        result = compute_effective_access(link, ctx, session, ORG_UUID)

        assert result == EffectiveAccess.WRITE

    def test_read_rule_gives_read_access(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx(username="user1", organization="org_a")
        session = _mock_session(access_result="READ")

        result = compute_effective_access(link, ctx, session, ORG_UUID)

        assert result == EffectiveAccess.READ

    def test_no_rules_gives_no_access(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx(username="user1", organization="org_a")
        session = _mock_session(access_result=None)

        result = compute_effective_access(link, ctx, session, ORG_UUID)

        assert result is None

    def test_empty_organization_gives_no_access(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx(username="user1", organization="")
        session = _mock_session(access_result=None)

        result = compute_effective_access(link, ctx, session, None)

        assert result is None


# ────────────────────────────────────────────────────────
# load_authorized_integrity_link
# ────────────────────────────────────────────────────────


class TestLoadAuthorizedIntegrityLinkNotFound:
    """load_authorized_integrity_link raises 404 when IntegrityLink not found."""

    def test_raises_404_when_not_found(self) -> None:
        session = MagicMock()
        session.get.return_value = None
        ctx = _geo_ctx()

        with pytest.raises(HTTPException) as exc_info:
            load_authorized_integrity_link(
                DATASET_ID, AccessLevel.METADATA_READ, ctx, session, None
            )

        assert exc_info.value.status_code == 404


class TestLoadAuthorizedIntegrityLinkAdminBypass:
    """Admin bypasses all access levels."""

    @pytest.mark.parametrize("level", list(AccessLevel))
    def test_admin_passes_any_level(self, level: AccessLevel) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx(is_admin=True)
        session = _mock_session(integrity_link=link, access_result="ADMIN")

        result = load_authorized_integrity_link(DATASET_ID, level, ctx, session, None)

        assert result is link


class TestLoadAuthorizedIntegrityLinkOwnerBypass:
    """Owner bypasses all access levels."""

    @pytest.mark.parametrize("level", list(AccessLevel))
    def test_owner_passes_any_level(self, level: AccessLevel) -> None:
        link = _integrity_link(owner="user1")
        ctx = _geo_ctx(username="user1")
        session = _mock_session(integrity_link=link, access_result="OWNER")

        result = load_authorized_integrity_link(DATASET_ID, level, ctx, session, None)

        assert result is link


class TestLoadAuthorizedIntegrityLinkMetadataRead:
    """METADATA_READ requires at least READ access."""

    def test_read_rule_allows_metadata_read(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx()
        session = _mock_session(integrity_link=link, access_result="READ")

        result = load_authorized_integrity_link(
            DATASET_ID, AccessLevel.METADATA_READ, ctx, session, ORG_UUID
        )

        assert result is link

    def test_write_rule_allows_metadata_read(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx()
        session = _mock_session(integrity_link=link, access_result="WRITE")

        result = load_authorized_integrity_link(
            DATASET_ID, AccessLevel.METADATA_READ, ctx, session, ORG_UUID
        )

        assert result is link

    def test_no_rule_raises_403(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx()
        session = _mock_session(integrity_link=link, access_result=None)

        with pytest.raises(HTTPException) as exc_info:
            load_authorized_integrity_link(
                DATASET_ID, AccessLevel.METADATA_READ, ctx, session, ORG_UUID
            )

        assert exc_info.value.status_code == 403


class TestLoadAuthorizedIntegrityLinkMetadataWrite:
    """METADATA_WRITE requires WRITE access (READ is insufficient)."""

    def test_write_rule_allows_metadata_write(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx()
        session = _mock_session(integrity_link=link, access_result="WRITE")

        result = load_authorized_integrity_link(
            DATASET_ID, AccessLevel.METADATA_WRITE, ctx, session, ORG_UUID
        )

        assert result is link

    def test_read_rule_raises_403_for_metadata_write(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx()
        session = _mock_session(integrity_link=link, access_result="READ")

        with pytest.raises(HTTPException) as exc_info:
            load_authorized_integrity_link(
                DATASET_ID, AccessLevel.METADATA_WRITE, ctx, session, ORG_UUID
            )

        assert exc_info.value.status_code == 403

    def test_no_rule_raises_403(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx()
        session = _mock_session(integrity_link=link, access_result=None)

        with pytest.raises(HTTPException) as exc_info:
            load_authorized_integrity_link(
                DATASET_ID, AccessLevel.METADATA_WRITE, ctx, session, ORG_UUID
            )

        assert exc_info.value.status_code == 403


class TestLoadAuthorizedIntegrityLinkOwnerOnly:
    """OWNER_ONLY rejects group-based access, only admin/owner pass."""

    def test_write_rule_raises_403_for_owner_only(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx()
        session = _mock_session(integrity_link=link, access_result="WRITE")

        with pytest.raises(HTTPException) as exc_info:
            load_authorized_integrity_link(
                DATASET_ID, AccessLevel.OWNER_ONLY, ctx, session, ORG_UUID
            )

        assert exc_info.value.status_code == 403

    def test_read_rule_raises_403_for_owner_only(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx()
        session = _mock_session(integrity_link=link, access_result="READ")

        with pytest.raises(HTTPException) as exc_info:
            load_authorized_integrity_link(
                DATASET_ID, AccessLevel.OWNER_ONLY, ctx, session, ORG_UUID
            )

        assert exc_info.value.status_code == 403

    def test_owner_passes_owner_only(self) -> None:
        link = _integrity_link(owner="user1")
        ctx = _geo_ctx(username="user1")
        session = _mock_session(integrity_link=link, access_result="OWNER")

        result = load_authorized_integrity_link(
            DATASET_ID, AccessLevel.OWNER_ONLY, ctx, session, None
        )

        assert result is link

    def test_admin_passes_owner_only(self) -> None:
        link = _integrity_link(owner="other")
        ctx = _geo_ctx(is_admin=True)
        session = _mock_session(integrity_link=link, access_result="ADMIN")

        result = load_authorized_integrity_link(
            DATASET_ID, AccessLevel.OWNER_ONLY, ctx, session, None
        )

        assert result is link


# ────────────────────────────────────────────────────────
# get_org_id
# ────────────────────────────────────────────────────────


class TestGetOrgId:
    """get_org_id dependency resolves org shortName to console UUID once per request."""

    def test_returns_none_when_no_organization(self) -> None:
        ctx = _geo_ctx(organization="")
        result = get_org_id(ctx)
        assert result is None

    @patch("src.api.deps.ConsoleService")
    def test_returns_uuid_when_org_found(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value.get_organization.return_value = {"id": "uuid-123", "name": "Org A"}
        ctx = _geo_ctx(organization="org_a")

        result = get_org_id(ctx)

        assert result == "uuid-123"
        mock_cls.return_value.get_organization.assert_called_once_with("org_a")

    @patch("src.api.deps.ConsoleService")
    def test_returns_none_when_org_not_found(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value.get_organization.return_value = None
        ctx = _geo_ctx(organization="unknown_org")

        result = get_org_id(ctx)

        assert result is None

    @patch("src.api.deps.ConsoleService")
    def test_returns_none_when_console_unreachable(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value.get_organization.return_value = None
        ctx = _geo_ctx(organization="org_a")

        result = get_org_id(ctx)

        assert result is None

    @patch("src.api.deps.ConsoleService")
    def test_returns_none_when_id_missing_from_response(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value.get_organization.return_value = {"name": "Org A"}  # no 'id' key
        ctx = _geo_ctx(organization="org_a")

        result = get_org_id(ctx)

        assert result is None
