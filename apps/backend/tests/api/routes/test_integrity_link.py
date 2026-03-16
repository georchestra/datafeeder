"""Tests for integrity_link API routes (single link endpoints)."""

from collections.abc import Iterator
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.api.routes.ingestion.integrity_link import (
    delete_integrity_link_rule,
    get_integrity_link,
    toggle_publish_gn_integrity_link,
    toggle_publish_gs_integrity_link,
    upsert_integrity_link_rule,
)
from src.core.security import EffectiveAccess
from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import (
    GROUP_OR_ROLE_EVERYONE,
    IntegrityLinkRule,
    RuleType,
    RuleValue,
    UpsertRuleRequest,
)
from src.models.recurrence import RecurrencePreset
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
            org_id=None,
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
            org_id=None,
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
                org_id=None,
                body=body,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "IntegrityLink not found"


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
            org_id=None,
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
                org_id=None,
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
                org_id=None,
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
                org_id=None,
                rule_id=7,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Rule not found"


class TestSyncAfterUpsertRule:
    """Test that GeoNetwork sharing is synced after rule mutations."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    def test_sync_called_when_metadata_id_set(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """sync_record_sharing is called after upsert when integrity_link has metadata_id."""
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
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.return_value = [
                {"id": "org-uuid-1", "shortName": "C2C", "name": "Camptocamp"}
            ]

            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                org_id=None,
                body=body,
            )

        mock_ms.sync_record_sharing.assert_called_once_with("meta-uuid", [("C2C", RuleValue.READ)])

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
                org_id=None,
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
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService"),
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            upsert_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                org_id=None,
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
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
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
                    org_id=None,
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
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
            patch("src.api.routes.ingestion.integrity_link.MetadataService"),
        ):
            mock_console = MagicMock()
            mock_console_cls.return_value = mock_console
            mock_console.get_all_organizations.side_effect = Exception("Console unavailable")

            with pytest.raises(HTTPException) as exc_info:
                upsert_integrity_link_rule(
                    session=mock_session,
                    georchestra_context=_geo_ctx(),
                    integrity_link_id=integrity_link_id,
                    org_id=None,
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
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
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
                    org_id=None,
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

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService"),
            patch("src.api.routes.ingestion.integrity_link.MetadataService") as mock_ms_cls,
        ):
            mock_ms = MagicMock()
            mock_ms_cls.return_value = mock_ms

            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                org_id=None,
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
                org_id=None,
                rule_id=7,
            )

        mock_ms.sync_record_sharing.assert_not_called()


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
        integrity_link = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            final_table_name="final_test",
            gs_is_published=False,
        )
        mock_session.get.return_value = integrity_link

        mock_gs = MagicMock()
        mock_gs.acl_layer_publish = MagicMock()
        mock_gs.acl_layer_get = MagicMock(return_value=["*", "GROUP_1"])

        # Only exec: query final rules after commit for the response
        final_rules_mock = MagicMock()
        final_rules_mock.all.return_value = []
        mock_session.exec.side_effect = [final_rules_mock]

        toggle_publish_gs_integrity_link(
            session=mock_session,
            georchestra_context=_geo_ctx(),
            org_id=None,
            geoserver_service=mock_gs,
            integrity_link_id=integrity_link_id,
            publish=True,
        )

        mock_gs.acl_layer_publish.assert_called_once()
        mock_gs.acl_layer_get.assert_called_once()
        mock_session.delete.assert_not_called()
        mock_session.add.assert_called()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert integrity_link.gs_is_published is True

    def test_unpublish_success_no_other_roles(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """When only EVERYONE rule exists, unpublish removes the ACL rule entirely."""
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
        mock_gs.acl_layer_unpublish = MagicMock()
        mock_gs.acl_layer_get = MagicMock(return_value=None)

        # First exec: query existing READ rules
        # Second exec: query final rules after commit for the response
        rules_mock = MagicMock()
        rules_mock.all.return_value = [everyone_rule]
        final_rules_mock = MagicMock()
        final_rules_mock.all.return_value = []
        mock_session.exec.side_effect = [rules_mock, final_rules_mock]

        toggle_publish_gs_integrity_link(
            session=mock_session,
            georchestra_context=_geo_ctx(),
            org_id=None,
            geoserver_service=mock_gs,
            integrity_link_id=integrity_link_id,
            publish=False,
        )

        mock_gs.acl_layer_unpublish.assert_called_once()
        mock_gs.acl_layer_get.assert_called_once()
        mock_session.delete.assert_called_once_with(everyone_rule)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()
        assert integrity_link.gs_is_published is False

    def test_unpublish_success_with_other_roles(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        """When other group rules exist, unpublish restores GeoServer ACL to those roles only."""
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
            group_or_role="GROUP_1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        with (
            patch("src.api.routes.ingestion.integrity_link.get_settings"),
            patch("src.api.routes.ingestion.integrity_link.ConsoleService") as mock_console_cls,
        ):
            mock_gs = MagicMock()
            mock_gs.acl_layer_add_rule = MagicMock()
            mock_gs.acl_layer_get = MagicMock(return_value=["ROLE_GROUP_1"])

            mock_console = MagicMock()
            mock_console.get_role_labels.return_value = ["ROLE_GROUP_1"]
            mock_console_cls.return_value = mock_console

            # First exec: query existing READ rules
            # Second exec: query final rules after commit for the response
            rules_mock = MagicMock()
            rules_mock.all.return_value = [everyone_rule, group_rule]
            final_rules_mock = MagicMock()
            final_rules_mock.all.return_value = [group_rule]
            mock_session.exec.side_effect = [rules_mock, final_rules_mock]

            toggle_publish_gs_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                org_id=None,
                geoserver_service=mock_gs,
                integrity_link_id=integrity_link_id,
                publish=False,
            )

        mock_gs.acl_layer_add_rule.assert_called_once()
        call_args = mock_gs.acl_layer_add_rule.call_args
        assert call_args.kwargs["roles"] == ["ROLE_GROUP_1"]
        mock_gs.acl_layer_get.assert_called_once()
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
                org_id=None,
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
                org_id=None,
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
        mock_gs.acl_layer_publish = MagicMock(side_effect=GeoServerAclError(500, "GeoServer error"))

        with pytest.raises(HTTPException) as exc_info:
            toggle_publish_gs_integrity_link(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                org_id=None,
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
            org_id=None,
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
            org_id=None,
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
            org_id=None,
        )

        assert result.schedule == "30 2 15 * *"
        assert result.preset_id is None
