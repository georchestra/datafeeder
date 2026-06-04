"""Tests for integrity_link API routes (single link endpoints)."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.api.routes.ingestion.integrity_link import (
    _sync_title_geoserver,  # type: ignore[reportPrivateUsage]
    delete_integrity_link_rule,
    get_integrity_link,
    toggle_publish_gn_integrity_link,
    toggle_publish_gs_integrity_link,
    update_metadata_gn,
    update_schedule,
    upsert_integrity_link_rule,
)
from src.core.security import EffectiveAccess
from src.models.data_import import ImportType, UpdateMetadataGnRequest
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import (
    GROUP_OR_ROLE_EVERYONE,
    IntegrityLinkRule,
    RuleType,
    RuleValue,
    UpsertRuleRequest,
)
from src.models.recurrence import RecurrencePreset
from src.services.console_service import ConsoleServiceError
from src.services.georchestra import GeorchestraContext
from src.services.geoserver import GeoServerAclError


def _geo_ctx() -> GeorchestraContext:
    return GeorchestraContext(
        username="testuser",
        roles=set(),
        email="",
        firstname="",
        lastname="",
        organization="",
    )


class TestUpsertIntegrityLinkRule:
    """Test the upsert_integrity_link_rule endpoint."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    def test_create_new_rule(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        # IntegrityLink exists
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
        )

        # First exec call: compute_effective_access → "OWNER"
        # Second exec call: look up existing rule → None (no rule exists)
        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        mock_session.exec.side_effect = [access_mock, no_rule_mock]

        body = UpsertRuleRequest(
            group_or_role="GROUP_1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        upsert_integrity_link_rule(
            session=mock_session,
            georchestra_context=_geo_ctx(),
            integrity_link_id=integrity_link_id,
            group_ids=[],
            body=body,
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        added_rule = mock_session.add.call_args[0][0]
        assert added_rule.integrity_link_id == UUID(integrity_link_id)
        assert added_rule.group_or_role == "GROUP_1"
        assert added_rule.rule_type == RuleType.DATA
        assert added_rule.rule_value == RuleValue.READ

    def test_update_existing_rule(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
        )

        existing_rule = IntegrityLinkRule(
            id=42,
            integrity_link_id=UUID(integrity_link_id),
            group_or_role="GROUP_1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )
        # First exec call: compute_effective_access → "OWNER"
        # Second exec call: look up existing rule → existing_rule
        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        rule_mock = MagicMock()
        rule_mock.first.return_value = existing_rule
        mock_session.exec.side_effect = [access_mock, rule_mock]

        body = UpsertRuleRequest(
            group_or_role="GROUP_1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.WRITE,
        )

        result = upsert_integrity_link_rule(
            session=mock_session,
            georchestra_context=_geo_ctx(),
            integrity_link_id=integrity_link_id,
            group_ids=[],
            body=body,
        )

        assert result.rule_value == RuleValue.WRITE
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(existing_rule)

    def test_integrity_link_not_found(self, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None

        body = UpsertRuleRequest(
            group_or_role="GROUP_1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with pytest.raises(HTTPException) as exc_info:
            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=str(uuid4()),
                group_ids=[],
                body=body,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "IntegrityLink not found"

    def test_gs_sync_error_rolls_back_and_returns_500(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """If GeoServer sync fails, the DB transaction is rolled back and HTTP 500 is returned."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="final_test",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        data_rules_mock = MagicMock()
        # Non-EVERYONE rule triggers UUID resolution → Console call → ConsoleServiceError
        data_rules_mock.all.return_value = [
            IntegrityLinkRule(
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="role-uuid-1",
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, data_rules_mock]

        body = UpsertRuleRequest(
            group_or_role="role-uuid-1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls,
        ):
            mock_console_cls.return_value.get_all_roles.side_effect = ConsoleServiceError(
                "console unreachable"
            )
            mock_gs_cls.return_value = MagicMock()

            with pytest.raises(HTTPException) as exc_info:
                upsert_integrity_link_rule(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    body=body,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.sync.geoserver"
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


class TestDeleteIntegrityLinkRule:
    """Test the delete_integrity_link_rule endpoint."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    def test_delete_existing_rule(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        mock_session.get.side_effect = [
            IntegrityLink(
                id=UUID(integrity_link_id),
                integrity_owner="testuser",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                staging_table_name="staging_test",
            ),  # first call: integrity_link
            IntegrityLinkRule(
                id=7,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="GROUP_1",
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            ),  # second call: rule
        ]
        mock_session.exec.return_value.first.return_value = "OWNER"

        response = delete_integrity_link_rule(
            session=mock_session,
            georchestra_context=_geo_ctx(),
            integrity_link_id=integrity_link_id,
            group_ids=[],
            rule_id=7,
        )

        assert response.status_code == 204
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_integrity_link_not_found(self, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=str(uuid4()),
                group_ids=[],
                rule_id=1,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "IntegrityLink not found"

    def test_rule_not_found(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        mock_session.get.side_effect = [
            IntegrityLink(
                id=UUID(integrity_link_id),
                integrity_owner="testuser",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                staging_table_name="staging_test",
            ),  # integrity_link exists
            None,  # rule not found
        ]
        mock_session.exec.return_value.first.return_value = "OWNER"

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                rule_id=999,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Rule not found"

    def test_rule_belongs_to_different_integrity_link(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        other_link_id = uuid4()
        mock_session.get.side_effect = [
            IntegrityLink(
                id=UUID(integrity_link_id),
                integrity_owner="testuser",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                staging_table_name="staging_test",
            ),  # integrity_link exists
            IntegrityLinkRule(
                id=7,
                integrity_link_id=other_link_id,  # belongs to a different link
                group_or_role="GROUP_1",
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            ),
        ]
        mock_session.exec.return_value.first.return_value = "OWNER"

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                rule_id=7,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Rule not found"

    def test_gs_sync_error_rolls_back_and_returns_500(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """If GeoServer sync fails during delete, the DB transaction is rolled back."""
        link = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="final_test",
        )
        data_rule = IntegrityLinkRule(
            id=7,
            integrity_link_id=UUID(integrity_link_id),
            group_or_role="role-uuid-1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )
        mock_session.get.side_effect = [link, data_rule]

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        data_rules_mock = MagicMock()
        # A remaining non-EVERYONE rule triggers UUID resolution → ConsoleServiceError
        data_rules_mock.all.return_value = [
            IntegrityLinkRule(
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="role-uuid-2",
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, data_rules_mock]

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls,
        ):
            mock_console_cls.return_value.get_all_roles.side_effect = ConsoleServiceError(
                "console unreachable"
            )
            mock_gs_cls.return_value = MagicMock()

            with pytest.raises(HTTPException) as exc_info:
                delete_integrity_link_rule(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    rule_id=7,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.sync.geoserver"
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


class TestSyncAfterUpsertRule:
    """Test that GeoNetwork sharing is synced after rule mutations."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    def _mock_settings(self, gn_sync_mode: str = "ORG") -> MagicMock:
        mock_settings = MagicMock()
        mock_settings.GN_SYNC_MODE = gn_sync_mode
        return mock_settings

    def test_sync_called_when_metadata_id_set(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_record_sharing is called after upsert when integrity_link has metadata_id.

        Uses mixed-case group_or_role vs lowercase GroupItem.id to verify case-insensitive lookup.
        """
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="meta-uuid",
        )

        # Three exec calls: access check, rule lookup, rules for sync
        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        rules_mock = MagicMock()
        rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="Org-Uuid-1",  # mixed case — must still resolve
                rule_type=RuleType.METADATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, rules_mock]

        body = UpsertRuleRequest(
            group_or_role="Org-Uuid-1",
            rule_type=RuleType.METADATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [
                {"id": "org-uuid-1", "shortName": "C2C"}  # lowercase id
            ]

            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=body,
            )

        mock_ms.sync_record_sharing.assert_called_once_with("meta-uuid", [("C2C", RuleValue.READ)])

    def test_sync_called_in_role_mode(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_record_sharing resolves group_or_role against roles in ROLE mode."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="meta-uuid",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        rules_mock = MagicMock()
        rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="role-uuid-1",
                rule_type=RuleType.METADATA,
                rule_value=RuleValue.WRITE,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, rules_mock]

        body = UpsertRuleRequest(
            group_or_role="role-uuid-1",
            rule_type=RuleType.METADATA,
            rule_value=RuleValue.WRITE,
        )

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings("ROLE"),
            ),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_roles.return_value = [{"id": "role-uuid-1", "name": "ROLE_ADMIN"}]

            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=body,
            )

        mock_console.get_all_roles.assert_called_once()
        mock_ms.sync_record_sharing.assert_called_once_with(
            "meta-uuid", [("ROLE_ADMIN", RuleValue.WRITE)]
        )

    def test_sync_not_called_when_no_metadata_id(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_record_sharing is not called when metadata_id is None."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id=None,
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        mock_session.exec.side_effect = [access_mock, no_rule_mock]

        body = UpsertRuleRequest(
            group_or_role="org-uuid-1",
            rule_type=RuleType.METADATA,
            rule_value=RuleValue.READ,
        )

        with patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls:
            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=body,
            )

        mock_ms.sync_record_sharing.assert_not_called()

    def test_sync_skips_non_metadata_rules(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """Only METADATA rules are passed to sync; DATA rules are ignored."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="meta-uuid",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        rules_mock = MagicMock()
        rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="org-uuid-1",
                rule_type=RuleType.DATA,  # DATA rule — should be skipped
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, rules_mock]

        body = UpsertRuleRequest(
            group_or_role="org-uuid-1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = []

            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=body,
            )

        # sync called with empty resolved list (DATA rule filtered out)
        mock_ms.sync_record_sharing.assert_called_once_with("meta-uuid", [])

    def test_raises_500_when_console_cannot_resolve_org(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """Unresolvable org ID causes HTTPException(500, i18nerror.sync.geonetwork)."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="meta-uuid",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        rules_mock = MagicMock()
        rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="org-uuid-unknown",
                rule_type=RuleType.METADATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, rules_mock]

        body = UpsertRuleRequest(
            group_or_role="org-uuid-unknown",
            rule_type=RuleType.METADATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.MetadataService"),
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            # org-uuid-unknown is not in the returned list
            mock_console.get_all_organizations.return_value = [
                {"id": "org-uuid-1", "shortName": "C2C"}
            ]

            with pytest.raises(HTTPException) as exc_info:
                upsert_integrity_link_rule(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    body=body,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.sync.geonetwork"

    def test_raises_500_when_console_call_fails(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """Console API failure causes HTTPException(500, i18nerror.sync.geonetwork)."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="meta-uuid",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        rules_mock = MagicMock()
        rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="org-uuid-1",
                rule_type=RuleType.METADATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, rules_mock]

        body = UpsertRuleRequest(
            group_or_role="org-uuid-1",
            rule_type=RuleType.METADATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.MetadataService"),
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.side_effect = Exception("console error")

            with pytest.raises(HTTPException) as exc_info:
                upsert_integrity_link_rule(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    body=body,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.sync.geonetwork"

    def test_raises_500_when_geonetwork_sync_fails(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """GeoNetwork sync failure causes HTTPException(500, i18nerror.sync.geonetwork)."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="meta-uuid",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        rules_mock = MagicMock()
        rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="org-uuid-1",
                rule_type=RuleType.METADATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, rules_mock]

        body = UpsertRuleRequest(
            group_or_role="org-uuid-1",
            rule_type=RuleType.METADATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings("ORG"),
            ),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [
                {"id": "org-uuid-1", "shortName": "C2C"}
            ]

            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms
            mock_ms.sync_record_sharing.side_effect = Exception("GeoNetwork down")

            with pytest.raises(HTTPException) as exc_info:
                upsert_integrity_link_rule(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    body=body,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.sync.geonetwork"


class TestSyncAfterDeleteRule:
    """Test that GeoNetwork sharing is synced after rule deletion."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    def test_sync_called_after_delete(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_record_sharing is called after rule deletion."""
        mock_session.get.side_effect = [
            IntegrityLink(
                id=UUID(integrity_link_id),
                integrity_owner="testuser",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                staging_table_name="staging_test",
                metadata_id="meta-uuid",
            ),
            IntegrityLinkRule(
                id=7,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="org-uuid-1",
                rule_type=RuleType.METADATA,
                rule_value=RuleValue.READ,
            ),
        ]

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        rules_mock = MagicMock()
        rules_mock.all.return_value = []  # All rules removed after delete
        mock_session.exec.side_effect = [access_mock, rules_mock]

        mock_settings = MagicMock()
        mock_settings.GN_SYNC_MODE = "ORG"

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=mock_settings,
            ),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = []

            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                rule_id=7,
            )

        # Sync called with empty list — clears all privileges
        mock_ms.sync_record_sharing.assert_called_once_with("meta-uuid", [])

    def test_sync_not_called_when_no_metadata_id(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_record_sharing is not called when metadata_id is None."""
        mock_session.get.side_effect = [
            IntegrityLink(
                id=UUID(integrity_link_id),
                integrity_owner="testuser",
                integrity_organization="testorg",
                source_import_type=ImportType.URL,
                staging_table_name="staging_test",
                metadata_id=None,
            ),
            IntegrityLinkRule(
                id=7,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="org-uuid-1",
                rule_type=RuleType.METADATA,
                rule_value=RuleValue.READ,
            ),
        ]
        mock_session.exec.return_value.first.return_value = "OWNER"

        with patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls:
            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                rule_id=7,
            )

        mock_ms.sync_record_sharing.assert_not_called()


class TestSyncDataSharingAfterUpsert:
    """Test that GeoServer ACL is synced after rule mutations."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    def test_gs_sync_called_when_layer_exists(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_layer_acl is called with resolved role names when final_table_name is set."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="MyOrg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="my_layer",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        data_rules_mock = MagicMock()
        data_rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="role-uuid-1",
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, data_rules_mock]

        body = UpsertRuleRequest(
            group_or_role="role-uuid-1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls,
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = [{"id": "role-uuid-1", "name": "GN_REVIEWER"}]
            mock_console_cls.return_value = mock_console

            mock_gs = MagicMock()
            mock_gs_cls.return_value = mock_gs

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=body,
            )

        mock_gs.sync_layer_acl.assert_called_once_with(
            "myorg", "my_layer", [("ROLE_GN_REVIEWER", RuleValue.READ)]
        )

    def test_gs_sync_not_called_when_no_layer(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_layer_acl is not called when final_table_name is None."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="MyOrg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name=None,
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        mock_session.exec.side_effect = [access_mock, no_rule_mock]

        body = UpsertRuleRequest(
            group_or_role="ROLE_IMPORT",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls:
            mock_gs = MagicMock()
            mock_gs_cls.return_value = mock_gs

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=body,
            )

        mock_gs.sync_layer_acl.assert_not_called()

    def test_gs_sync_filters_metadata_rules(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """Only DATA rules are passed to GeoServer; METADATA rules are ignored."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="MyOrg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="my_layer",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        all_rules_mock = MagicMock()
        all_rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="role-uuid-1",
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            ),
            IntegrityLinkRule(
                id=2,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="org-uuid-1",
                rule_type=RuleType.METADATA,  # should be filtered out
                rule_value=RuleValue.READ,
            ),
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, all_rules_mock]

        body = UpsertRuleRequest(
            group_or_role="role-uuid-1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls,
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = [{"id": "role-uuid-1", "name": "GN_REVIEWER"}]
            mock_console_cls.return_value = mock_console

            mock_gs = MagicMock()
            mock_gs_cls.return_value = mock_gs

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=body,
            )

        mock_gs.sync_layer_acl.assert_called_once_with(
            "myorg", "my_layer", [("ROLE_GN_REVIEWER", RuleValue.READ)]
        )

    def test_gs_sync_raises_500_on_failure(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_layer_acl failure causes HTTPException(500, i18nerror.sync.geoserver)."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="MyOrg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="my_layer",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        data_rules_mock = MagicMock()
        data_rules_mock.all.return_value = []
        mock_session.exec.side_effect = [access_mock, no_rule_mock, data_rules_mock]

        body = UpsertRuleRequest(
            group_or_role="role-uuid-1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls,
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = []
            mock_console_cls.return_value = mock_console

            mock_gs = MagicMock()
            mock_gs_cls.return_value = mock_gs
            mock_gs.sync_layer_acl.side_effect = GeoServerAclError(500, "GeoServer down")

            with pytest.raises(HTTPException) as exc_info:
                upsert_integrity_link_rule(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    body=body,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.sync.geoserver"

    def test_gs_sync_called_after_delete(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_layer_acl is triggered after rule deletion with empty resolved list."""
        mock_session.get.side_effect = [
            IntegrityLink(
                id=UUID(integrity_link_id),
                integrity_owner="testuser",
                integrity_organization="MyOrg",
                source_import_type=ImportType.URL,
                staging_table_name="staging_test",
                final_table_name="my_layer",
            ),
            IntegrityLinkRule(
                id=7,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="role-uuid-1",
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            ),
        ]

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        data_rules_mock = MagicMock()
        data_rules_mock.all.return_value = []  # all rules removed after delete
        mock_session.exec.side_effect = [access_mock, data_rules_mock]

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls,
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = []
            mock_console_cls.return_value = mock_console

            mock_gs = MagicMock()
            mock_gs_cls.return_value = mock_gs

            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                rule_id=7,
            )

        mock_gs.sync_layer_acl.assert_called_once_with("myorg", "my_layer", [])

    def test_gs_sync_passes_everyone_rule_without_console(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """EVERYONE rule (*) is passed directly to sync without Console resolution."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="MyOrg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="my_layer",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        all_rules_mock = MagicMock()
        all_rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role=GROUP_OR_ROLE_EVERYONE,
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, all_rules_mock]

        body = UpsertRuleRequest(
            group_or_role="role-uuid-1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls,
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = []
            mock_console_cls.return_value = mock_console

            mock_gs = MagicMock()
            mock_gs_cls.return_value = mock_gs

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=body,
            )

        mock_gs.sync_layer_acl.assert_called_once_with("myorg", "my_layer", [("*", RuleValue.READ)])

    def test_gs_sync_raises_500_when_console_fails(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """Console API failure causes HTTPException(500, i18nerror.sync.geoserver)."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="MyOrg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="my_layer",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        data_rules_mock = MagicMock()
        data_rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="role-uuid-1",
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, data_rules_mock]

        body = UpsertRuleRequest(
            group_or_role="role-uuid-1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.GeoServerService"),
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.side_effect = ConsoleServiceError("Console unreachable")
            mock_console_cls.return_value = mock_console

            with pytest.raises(HTTPException) as exc_info:
                upsert_integrity_link_rule(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    body=body,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.sync.geoserver"

    def test_gs_sync_raises_500_when_role_not_found(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """Unresolvable role UUID causes HTTPException(500, i18nerror.sync.geoserver)."""
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="MyOrg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="my_layer",
        )

        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        data_rules_mock = MagicMock()
        data_rules_mock.all.return_value = [
            IntegrityLinkRule(
                id=1,
                integrity_link_id=UUID(integrity_link_id),
                group_or_role="role-uuid-unknown",
                rule_type=RuleType.DATA,
                rule_value=RuleValue.READ,
            )
        ]
        mock_session.exec.side_effect = [access_mock, no_rule_mock, data_rules_mock]

        body = UpsertRuleRequest(
            group_or_role="role-uuid-unknown",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.GeoServerService"),
        ):
            # role-uuid-unknown is not in the returned list
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = [{"id": "role-uuid-1", "name": "GN_REVIEWER"}]
            mock_console_cls.return_value = mock_console

            with pytest.raises(HTTPException) as exc_info:
                upsert_integrity_link_rule(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    body=body,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.sync.geoserver"


class TestTogglePublishGnIntegrityLink:
    """Test the toggle_publish_gn_integrity_link endpoint."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    def test_publish_success(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        integrity_link = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="some-metadata-uuid",
            gn_is_published=False,
            gs_is_published=False,
        )
        mock_session.get.return_value = integrity_link

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            toggle_publish_gn_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                publish=True,
            )

        mock_ms.toggle_publish_metadata_record.assert_called_once_with("some-metadata-uuid", True)
        assert integrity_link.gn_is_published is True
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    def test_unpublish_success(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        integrity_link = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="some-metadata-uuid",
            gn_is_published=True,
            gs_is_published=False,
        )
        mock_session.get.return_value = integrity_link

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            toggle_publish_gn_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                publish=False,
            )

        mock_ms.toggle_publish_metadata_record.assert_called_once_with("some-metadata-uuid", False)
        assert integrity_link.gn_is_published is False
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    def test_integrity_link_not_found(self, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            toggle_publish_gn_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=str(uuid4()),
                publish=True,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "IntegrityLink not found"

    def test_no_metadata_id(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            toggle_publish_gn_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                publish=True,
            )

        assert exc_info.value.status_code == 400
        assert (
            exc_info.value.detail == "IntegrityLink has no associated metadata to publish/unpublish"
        )

    def test_metadata_service_failure(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="some-metadata-uuid",
        )

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms
            mock_ms.toggle_publish_metadata_record.side_effect = Exception("GeoNetwork error")

            with pytest.raises(HTTPException) as exc_info:
                toggle_publish_gn_integrity_link(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    publish=True,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.publish.geonetwork"


class TestTogglePublishGsIntegrityLink:
    """Test the toggle_publish_gs_integrity_link endpoint."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    @pytest.fixture(autouse=True)
    def patch_load_authorized(self, mock_session: MagicMock) -> Iterator[None]:
        """Bypass load_authorized_integrity_link: return the mocked integrity link or 404."""

        def _load(integrity_link_id: str, *args: object, **kwargs: object):
            il = mock_session.get.return_value
            if il is None:
                raise HTTPException(status_code=404, detail="IntegrityLink not found")
            return il, EffectiveAccess.OWNER

        with patch(
            "src.api.routes.ingestion.integrity_link.load_authorized_integrity_link",
            side_effect=_load,
        ):
            yield

    def test_publish_success(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        """Publish syncs ALL DataKern DATA rules (not just EVERYONE) so individual roles are kept."""
        integrity_link = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testorg",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="final_test",
            gs_is_published=False,
        )
        mock_session.get.return_value = integrity_link

        everyone_rule = IntegrityLinkRule(
            integrity_link_id=UUID(integrity_link_id),
            group_or_role=GROUP_OR_ROLE_EVERYONE,
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        mock_gs = MagicMock()
        mock_gs.sync_layer_acl = MagicMock()
        mock_gs.acl_layer_get = MagicMock(return_value=["*"])

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = []
            mock_console_cls.return_value = mock_console

            # First exec: _sync_data_sharing queries all DATA rules (sees newly added EVERYONE)
            # Second exec: response rules query after commit
            data_rules_mock = MagicMock()
            data_rules_mock.all.return_value = [everyone_rule]
            final_rules_mock = MagicMock()
            final_rules_mock.all.return_value = [everyone_rule]
            mock_session.exec.side_effect = [data_rules_mock, final_rules_mock]

            toggle_publish_gs_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                group_ids=[],
                geoserver_service=mock_gs,
                integrity_link_id=integrity_link_id,
                publish=True,
            )

        mock_gs.sync_layer_acl.assert_called_once_with(
            "testorg", "final_test", [("*", RuleValue.READ)]
        )
        mock_gs.acl_layer_get.assert_called_once()
        mock_session.delete.assert_not_called()
        mock_session.add.assert_called()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert integrity_link.gs_is_published is True

    def test_unpublish_success_no_other_roles(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """When only EVERYONE rule exists, unpublish removes it from DB and re-syncs GeoServer with no roles."""
        integrity_link = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="final_test",
            gs_is_published=True,
        )
        mock_session.get.return_value = integrity_link
        everyone_rule = IntegrityLinkRule(
            id=2,
            integrity_link_id=UUID(integrity_link_id),
            group_or_role=GROUP_OR_ROLE_EVERYONE,
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        mock_gs = MagicMock()
        mock_gs.sync_layer_acl = MagicMock()
        mock_gs.acl_layer_get = MagicMock(return_value=None)

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = []
            mock_console_cls.return_value = mock_console

            # exec 1: query EVERYONE READ rules (for DB deletion)
            # exec 2: _sync_data_sharing queries all rules → no remaining DATA rules
            # exec 3: final rules for response
            everyone_rules_mock = MagicMock()
            everyone_rules_mock.all.return_value = [everyone_rule]
            data_rules_mock = MagicMock()
            data_rules_mock.all.return_value = []
            final_rules_mock = MagicMock()
            final_rules_mock.all.return_value = []
            mock_session.exec.side_effect = [everyone_rules_mock, data_rules_mock, final_rules_mock]

            toggle_publish_gs_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                group_ids=[],
                geoserver_service=mock_gs,
                integrity_link_id=integrity_link_id,
                publish=False,
            )

        mock_gs.acl_layer_remove_rule.assert_not_called()
        mock_gs.sync_layer_acl.assert_called_once_with("testorg", "final_test", [])
        mock_gs.acl_layer_get.assert_called_once()
        mock_session.delete.assert_called_once_with(everyone_rule)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert integrity_link.gs_is_published is False

    def test_unpublish_success_with_other_roles(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """When role-specific rules exist alongside EVERYONE, unpublish re-syncs GeoServer with individual roles."""
        integrity_link = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="final_test",
            gs_is_published=True,
        )
        mock_session.get.return_value = integrity_link
        everyone_rule = IntegrityLinkRule(
            id=2,
            integrity_link_id=UUID(integrity_link_id),
            group_or_role=GROUP_OR_ROLE_EVERYONE,
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )
        group_rule = IntegrityLinkRule(
            id=3,
            integrity_link_id=UUID(integrity_link_id),
            group_or_role="group-uuid-1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        mock_gs = MagicMock()
        mock_gs.sync_layer_acl = MagicMock()
        mock_gs.acl_layer_get = MagicMock(return_value=["ROLE_GROUP_1"])

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = [{"id": "group-uuid-1", "name": "GROUP_1"}]
            mock_console_cls.return_value = mock_console

            # exec 1: query EVERYONE READ rules (for DB deletion)
            # exec 2: _sync_data_sharing queries all rules → only group_rule remains
            # exec 3: final rules for response
            everyone_rules_mock = MagicMock()
            everyone_rules_mock.all.return_value = [everyone_rule]
            data_rules_mock = MagicMock()
            data_rules_mock.all.return_value = [group_rule]
            final_rules_mock = MagicMock()
            final_rules_mock.all.return_value = [group_rule]
            mock_session.exec.side_effect = [everyone_rules_mock, data_rules_mock, final_rules_mock]

            toggle_publish_gs_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                group_ids=[],
                geoserver_service=mock_gs,
                integrity_link_id=integrity_link_id,
                publish=False,
            )

        mock_gs.acl_layer_remove_rule.assert_not_called()
        # GeoServer is re-synced with individual roles only (EVERYONE excluded)
        mock_gs.sync_layer_acl.assert_called_once_with(
            "testorg", "final_test", [("ROLE_GROUP_1", RuleValue.READ)]
        )
        mock_gs.acl_layer_get.assert_called_once()
        # Only the EVERYONE rule deleted from DB, group_rule preserved
        mock_session.delete.assert_called_once_with(everyone_rule)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert integrity_link.gs_is_published is False

    def test_integrity_link_not_found(self, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            toggle_publish_gs_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                group_ids=[],
                geoserver_service=MagicMock(),
                integrity_link_id=str(uuid4()),
                publish=True,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "IntegrityLink not found"

    def test_no_final_table_name(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name=None,
        )

        with pytest.raises(HTTPException) as exc_info:
            toggle_publish_gs_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                group_ids=[],
                geoserver_service=MagicMock(),
                integrity_link_id=integrity_link_id,
                publish=True,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "IntegrityLink has no associated layer to publish/unpublish"

    def test_geoserver_service_failure(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="final_test",
        )

        mock_gs = MagicMock()
        mock_gs.sync_layer_acl = MagicMock(side_effect=GeoServerAclError(500, "GeoServer error"))

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
        ):
            mock_console = MagicMock()
            mock_console.get_all_roles.return_value = []
            mock_console_cls.return_value = mock_console

            data_rules_mock = MagicMock()
            data_rules_mock.all.return_value = []
            mock_session.exec.side_effect = [data_rules_mock]

            with pytest.raises(HTTPException) as exc_info:
                toggle_publish_gs_integrity_link(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    group_ids=[],
                    geoserver_service=mock_gs,
                    integrity_link_id=integrity_link_id,
                    publish=True,
                )

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "i18nerror.publish.geoserver"


class TestGetIntegrityLinkPresetId:
    """Test that get_integrity_link populates preset_id on the response."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    def _link(self, link_id: str, schedule: str | None) -> IntegrityLink:
        return IntegrityLink(
            id=UUID(link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            schedule=schedule,
            schedule_enabled=schedule is not None,
        )

    def test_known_preset_returns_preset_id(self, mock_session: MagicMock) -> None:
        link_id = str(uuid4())
        cron = RecurrencePreset.EVERY_DAY.cron
        mock_session.get.return_value = self._link(link_id, cron)
        mock_session.exec.return_value.first.return_value = "OWNER"

        result = get_integrity_link(
            session=mock_session,
            geo_ctx=_geo_ctx(),
            integrity_link_id=link_id,
            group_ids=[],
        )

        assert result.schedule == cron
        assert result.preset_id == "EVERY_DAY"

    def test_null_schedule_returns_preset_id_null(self, mock_session: MagicMock) -> None:
        link_id = str(uuid4())
        mock_session.get.return_value = self._link(link_id, None)
        mock_session.exec.return_value.first.return_value = "OWNER"

        result = get_integrity_link(
            session=mock_session,
            geo_ctx=_geo_ctx(),
            integrity_link_id=link_id,
            group_ids=[],
        )

        assert result.schedule is None
        assert result.preset_id is None

    def test_custom_cron_returns_preset_id_null(self, mock_session: MagicMock) -> None:
        link_id = str(uuid4())
        mock_session.get.return_value = self._link(link_id, "30 2 15 * *")
        mock_session.exec.return_value.first.return_value = "OWNER"

        result = get_integrity_link(
            session=mock_session,
            geo_ctx=_geo_ctx(),
            integrity_link_id=link_id,
            group_ids=[],
        )

        assert result.schedule == "30 2 15 * *"
        assert result.preset_id is None


class TestUpdateMetadataGn:
    """Tests for PUT /{integrity_link_id}/metadata-gn."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    def _link(self, link_id: str) -> IntegrityLink:
        return IntegrityLink(
            id=UUID(link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            integrity_title="Old Title",
        )

    def _body(self, title: str = "New Title") -> UpdateMetadataGnRequest:
        return UpdateMetadataGnRequest(
            serialized_xml="<xml>metadata</xml>",
            title=title,
        )

    def _mock_settings(self) -> MagicMock:
        s = MagicMock()
        s.GEONETWORK_URL = "http://geonetwork"
        s.DATADIR_PATH = "/datadir"
        s.GEONETWORK_USERNAME = "admin"
        s.GEONETWORK_PASSWORD = "password"
        return s

    def test_uploads_xml_and_commits_title(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """Happy path: XML uploaded to GN and integrity_title committed."""
        mock_session.get.return_value = self._link(integrity_link_id)
        mock_session.exec.return_value.first.return_value = "OWNER"

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            update_metadata_gn(
                session=mock_session,
                geo_ctx=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=self._body("New Title"),
            )

        mock_ms.upload_metadata_xml.assert_called_once_with(b"<xml>metadata</xml>")
        # integrity_title updated before commit
        link = mock_session.add.call_args[0][0]
        assert link.integrity_title == "New Title"
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()

    def test_returns_integrity_link_response(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """Endpoint returns an IntegrityLinkResponse built from the refreshed link."""
        link = self._link(integrity_link_id)
        mock_session.get.return_value = link
        mock_session.exec.return_value.first.return_value = "OWNER"

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.ingestion.integrity_link.MetadataService"),
        ):
            result = update_metadata_gn(
                session=mock_session,
                geo_ctx=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=self._body("New Title"),
            )

        assert result.id == UUID(integrity_link_id)
        assert result.integrity_title == "New Title"

    def test_raises_502_when_geonetwork_upload_fails(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """GeoNetwork upload failure → HTTP 502 with i18nerror.save.geonetwork."""
        mock_session.get.return_value = self._link(integrity_link_id)
        mock_session.exec.return_value.first.return_value = "OWNER"

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_ms_cls.return_value.upload_metadata_xml.side_effect = Exception("GN down")

            with pytest.raises(HTTPException) as exc_info:
                update_metadata_gn(
                    session=mock_session,
                    geo_ctx=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    body=self._body(),
                )

        assert exc_info.value.status_code == 502
        assert exc_info.value.detail == "i18nerror.save.geonetwork"
        mock_session.commit.assert_not_called()

    def test_does_not_commit_when_geonetwork_upload_fails(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """DB is not updated when GeoNetwork upload fails."""
        link = self._link(integrity_link_id)
        mock_session.get.return_value = link
        mock_session.exec.return_value.first.return_value = "OWNER"

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_ms_cls.return_value.upload_metadata_xml.side_effect = Exception("GN down")

            with pytest.raises(HTTPException):
                update_metadata_gn(
                    session=mock_session,
                    geo_ctx=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    group_ids=[],
                    body=self._body("New Title"),
                )

        mock_session.commit.assert_not_called()
        # the same object returned by session.get must not have been mutated
        assert link.integrity_title == "Old Title"

    def test_geoserver_sync_failure_is_non_blocking(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """GeoServer title sync failure is logged but does not block the commit."""
        mock_session.get.return_value = self._link(integrity_link_id)
        mock_session.exec.return_value.first.return_value = "OWNER"

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.ingestion.integrity_link.MetadataService"),
            patch(
                "src.api.routes.ingestion.integrity_link._sync_title_geoserver",
                side_effect=Exception("GeoServer down"),
            ),
        ):
            update_metadata_gn(
                session=mock_session,
                geo_ctx=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                body=self._body("New Title"),
            )

        # DB commit still happens despite GeoServer failure
        mock_session.commit.assert_called_once()
        link = mock_session.add.call_args[0][0]
        assert link.integrity_title == "New Title"

    def test_raises_404_when_integrity_link_not_found(self, mock_session: MagicMock) -> None:
        """Unknown integrity_link_id → HTTP 404."""
        mock_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            update_metadata_gn(
                session=mock_session,
                geo_ctx=_geo_ctx(),
                integrity_link_id=str(uuid4()),
                group_ids=[],
                body=self._body(),
            )

        assert exc_info.value.status_code == 404


class TestSyncTitleGeoserver:
    """Tests for _sync_title_geoserver."""

    def _link(self, final_table_name: str | None = "my_table") -> IntegrityLink:
        return IntegrityLink(
            id=uuid4(),
            integrity_owner="testuser",
            integrity_organization="TestOrg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name=final_table_name,
        )

    def _mock_settings(self) -> MagicMock:
        s = MagicMock()
        s.GEOSERVER_INTERNAL_URL = "http://geoserver"
        s.GEOSERVER_USER = "admin"
        s.GEOSERVER_PASSWORD = "password"
        s.DATA_PUBLIC_URL = "http://public"
        return s

    def test_skips_when_final_table_name_is_none(self) -> None:
        """No GeoServer call when the layer has not been published yet."""
        with patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls:
            _sync_title_geoserver("Any Title", self._link(final_table_name=None))
            mock_gs_cls.assert_not_called()

    def test_calls_update_layer_title_with_lowercased_org(self) -> None:
        """Workspace is the lowercased integrity_organization; datastore follows {workspace}_ds convention."""
        link = self._link()

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls,
        ):
            mock_gs = MagicMock()
            mock_gs_cls.return_value = mock_gs

            _sync_title_geoserver("New Title", link)

        mock_gs.update_layer_title.assert_called_once_with(
            "testorg", "testorg_ds", "my_table", "New Title"
        )

    def test_propagates_geoserver_acl_error(self) -> None:
        """GeoServerAclError bubbles up so the endpoint can handle it as non-blocking."""
        link = self._link()

        with (
            patch(
                "src.api.routes.ingestion.integrity_link.get_settings",
                return_value=self._mock_settings(),
            ),
            patch("src.api.routes.ingestion.integrity_link.GeoServerService") as mock_gs_cls,
        ):
            mock_gs_cls.return_value.update_layer_title.side_effect = GeoServerAclError(500, "err")

            with pytest.raises(GeoServerAclError):
                _sync_title_geoserver("New Title", link)


class TestUpdateSchedule:
    """Test the update_schedule PATCH /{integrity_link_id}/schedule endpoint."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    @pytest.fixture(autouse=True)
    def patch_load_authorized(self, mock_session: MagicMock) -> Iterator[None]:
        def _load(integrity_link_id: str, *args: object, **kwargs: object):
            il = mock_session.get.return_value
            if il is None:
                raise HTTPException(status_code=404, detail="IntegrityLink not found")
            return il, EffectiveAccess.OWNER

        with patch(
            "src.api.routes.ingestion.integrity_link.load_authorized_integrity_link",
            side_effect=_load,
        ):
            yield

    def _link(self, link_id: str) -> IntegrityLink:
        return IntegrityLink(
            id=UUID(link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
        )

    def test_set_preset_enables_schedule(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        integrity_link = self._link(integrity_link_id)
        mock_session.get.return_value = integrity_link

        result = update_schedule(
            session=mock_session,
            geo_ctx=_geo_ctx(),
            integrity_link_id=integrity_link_id,
            group_ids=[],
            preset=RecurrencePreset.EVERY_DAY,
        )

        assert integrity_link.schedule == RecurrencePreset.EVERY_DAY.cron
        assert integrity_link.schedule_enabled is True
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(integrity_link)
        assert result.schedule == RecurrencePreset.EVERY_DAY.cron
        assert result.preset_id == "EVERY_DAY"

    def test_clear_preset_disables_schedule(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        integrity_link = self._link(integrity_link_id)
        integrity_link.schedule = RecurrencePreset.EVERY_DAY.cron
        integrity_link.schedule_enabled = True
        mock_session.get.return_value = integrity_link

        result = update_schedule(
            session=mock_session,
            geo_ctx=_geo_ctx(),
            integrity_link_id=integrity_link_id,
            group_ids=[],
            preset=None,
        )

        assert integrity_link.schedule is None
        assert integrity_link.schedule_enabled is False
        mock_session.commit.assert_called_once()
        assert result.schedule is None
        assert result.preset_id is None

    def test_not_found_raises_404(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        mock_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            update_schedule(
                session=mock_session,
                geo_ctx=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                group_ids=[],
                preset=RecurrencePreset.EVERY_WEEK,
            )

        assert exc_info.value.status_code == 404
