"""Tests for integrity_link API routes (single link endpoints)."""

from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.api.routes.ingestion.integrity_link import (
    delete_integrity_link_rule,
    upsert_integrity_link_rule,
)
from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import (
    IntegrityLinkRule,
    RuleType,
    RuleValue,
    UpsertRuleRequest,
)
from src.services.georchestra import GeorchestraContext


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
