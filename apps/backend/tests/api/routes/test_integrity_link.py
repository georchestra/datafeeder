"""Tests for integrity_link API routes (single link endpoints)."""

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

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
        from src.api.routes.ingestion.integrity_link import upsert_integrity_link_rule

        # IntegrityLink exists
        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
        )

        # No existing rule found
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = None
        mock_session.exec.return_value = mock_exec_result

        body = UpsertRuleRequest(
            group_or_role="GROUP_1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.READ,
        )

        upsert_integrity_link_rule(
            session=mock_session,
            georchestra_context=_geo_ctx(),
            integrity_link_id=integrity_link_id,
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
        from src.api.routes.ingestion.integrity_link import upsert_integrity_link_rule

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
        mock_exec_result = MagicMock()
        mock_exec_result.first.return_value = existing_rule
        mock_session.exec.return_value = mock_exec_result

        body = UpsertRuleRequest(
            group_or_role="GROUP_1",
            rule_type=RuleType.DATA,
            rule_value=RuleValue.WRITE,
        )

        result = upsert_integrity_link_rule(
            session=mock_session,
            georchestra_context=_geo_ctx(),
            integrity_link_id=integrity_link_id,
            body=body,
        )

        assert result.rule_value == RuleValue.WRITE
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(existing_rule)

    def test_integrity_link_not_found(self, mock_session: MagicMock) -> None:
        from src.api.routes.ingestion.integrity_link import upsert_integrity_link_rule

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
        from src.api.routes.ingestion.integrity_link import delete_integrity_link_rule

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

        response = delete_integrity_link_rule(
            session=mock_session,
            georchestra_context=_geo_ctx(),
            integrity_link_id=integrity_link_id,
            rule_id=7,
        )

        assert response.status_code == 204
        mock_session.delete.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_integrity_link_not_found(self, mock_session: MagicMock) -> None:
        from src.api.routes.ingestion.integrity_link import delete_integrity_link_rule

        mock_session.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=str(uuid4()),
                rule_id=1,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "IntegrityLink not found"

    def test_rule_not_found(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        from src.api.routes.ingestion.integrity_link import delete_integrity_link_rule

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

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                rule_id=999,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Rule not found"

    def test_rule_belongs_to_different_integrity_link(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        from src.api.routes.ingestion.integrity_link import delete_integrity_link_rule

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

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(
                session=mock_session,
                georchestra_context=_geo_ctx(),
                integrity_link_id=integrity_link_id,
                rule_id=7,
            )

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Rule not found"


class TestTogglePublishGnIntegrityLink:
    """Test the toggle_publish_gn_integrity_link endpoint."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def integrity_link_id(self) -> str:
        return str(uuid4())

    def test_publish_success(self, mock_session: MagicMock, integrity_link_id: str) -> None:
        from src.api.routes.ingestion.integrity_link import toggle_publish_gn_integrity_link

        integrity_link = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="some-metadata-uuid",
            gn_is_published=False,
        )
        mock_session.get.return_value = integrity_link

        with patch("src.api.routes.ingestion.integrity_link.get_settings"), patch(
            "src.api.routes.ingestion.integrity_link.MetadataService"
        ) as mock_ms_cls:
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
        from src.api.routes.ingestion.integrity_link import toggle_publish_gn_integrity_link

        integrity_link = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="some-metadata-uuid",
            gn_is_published=True,
        )
        mock_session.get.return_value = integrity_link

        with patch("src.api.routes.ingestion.integrity_link.get_settings"), patch(
            "src.api.routes.ingestion.integrity_link.MetadataService"
        ) as mock_ms_cls:
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
        from src.api.routes.ingestion.integrity_link import toggle_publish_gn_integrity_link

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
        from src.api.routes.ingestion.integrity_link import toggle_publish_gn_integrity_link

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
        assert exc_info.value.detail == "IntegrityLink has no associated metadata to publish/unpublish"

    def test_metadata_service_failure(
        self, mock_session: MagicMock, integrity_link_id: str
    ) -> None:
        from src.api.routes.ingestion.integrity_link import toggle_publish_gn_integrity_link

        mock_session.get.return_value = IntegrityLink(
            id=UUID(integrity_link_id),
            integrity_owner="testuser",
            integrity_organization="testorg",
            source_import_type=ImportType.URL,
            staging_table_name="staging_test",
            metadata_id="some-metadata-uuid",
        )

        with patch("src.api.routes.ingestion.integrity_link.get_settings"), patch(
            "src.api.routes.ingestion.integrity_link.MetadataService"
        ) as mock_ms_cls:
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
