"""Integration tests: verify each protected endpoint enforces permissions.

Each test class covers one protected endpoint, testing:
- 403 when the user has no matching access (no rules, not owner, not admin)
- Success (200/204) when the user is authorized (owner in these tests)
- Correct AccessLevel enforcement via WRITE/READ group user tests:
  - METADATA_WRITE endpoints: WRITE group → pass, READ group → 403
  - OWNER_ONLY endpoints: WRITE group → 403
"""

from unittest.mock import ANY, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.core.security import AccessLevel
from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.models.integrity_link_rule import RuleType, RuleValue, UpsertRuleRequest
from src.services.georchestra import GeorchestraContext

INTLINK_ID = str(uuid4())
INTLINK_UUID = UUID(INTLINK_ID)

# A non-None org UUID to exercise group-access code paths in tests.
ORG_UUID = "test-org-uuid-1234"


def _link(owner: str = "owner1") -> IntegrityLink:
    """Return a minimal IntegrityLink stub."""
    return IntegrityLink(
        id=INTLINK_UUID,
        integrity_owner=owner,
        integrity_organization="org_a",
        source_import_type=ImportType.URL,
        staging_table_name="staging_test",
    )


def _ctx(username: str = "stranger", organization: str = "other_org") -> GeorchestraContext:
    """Unauthorized context (no rules, not owner, not admin)."""
    return GeorchestraContext(
        username=username,
        roles={"IMPORT"},
        email="",
        firstname="",
        lastname="",
        organization=organization,
    )


def _owner_ctx() -> GeorchestraContext:
    """Authorized context — dataset owner."""
    return GeorchestraContext(
        username="owner1",
        roles={"IMPORT"},
        email="",
        firstname="",
        lastname="",
        organization="org_a",
    )


def _write_ctx() -> GeorchestraContext:
    """User whose organization has a METADATA WRITE rule (not owner, not admin)."""
    return GeorchestraContext(
        username="writer1",
        roles={"IMPORT"},
        email="",
        firstname="",
        lastname="",
        organization="org_a",
    )


def _read_ctx() -> GeorchestraContext:
    """User whose organization has a METADATA READ rule (not owner, not admin)."""
    return GeorchestraContext(
        username="reader1",
        roles={"IMPORT"},
        email="",
        firstname="",
        lastname="",
        organization="org_a",
    )


def _admin_ctx() -> GeorchestraContext:
    """Admin context (not owner)."""
    return GeorchestraContext(
        username="admin1",
        roles={"ADMINISTRATOR", "IMPORT"},
        email="",
        firstname="",
        lastname="",
        organization="other_org",
    )


def _mock_session(link: IntegrityLink | None = None) -> MagicMock:
    """Session that returns *link* on `session.get(...)` and no rules."""
    session = MagicMock()
    session.get.return_value = link
    mock_exec = MagicMock()
    mock_exec.all.return_value = []  # no rules → no group access
    session.exec.return_value = mock_exec
    return session


def _mock_session_with_rule(link: IntegrityLink, rule_value: RuleValue) -> MagicMock:
    """Session that returns *link* and a single METADATA rule with given value."""
    session = MagicMock()
    session.get.return_value = link
    rule = MagicMock()
    rule.rule_value = rule_value
    mock_exec = MagicMock()
    mock_exec.all.return_value = [rule]
    session.exec.return_value = mock_exec
    return session


# ────────────────────────────────────────────────────────
# GET /ingestion/integrity-link/{id}  (METADATA_WRITE)
# ────────────────────────────────────────────────────────


class TestGetIntegrityLinkPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.integrity_link import get_integrity_link

        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_integrity_link(session, _ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_read_group_user(self) -> None:
        """READ group access is insufficient for METADATA_WRITE endpoint."""
        from src.api.routes.ingestion.integrity_link import get_integrity_link

        session = _mock_session_with_rule(_link(), RuleValue.READ)

        with pytest.raises(HTTPException) as exc_info:
            get_integrity_link(session, _read_ctx(), INTLINK_ID, ORG_UUID)

        assert exc_info.value.status_code == 403

    def test_returns_entity_for_owner(self) -> None:
        from src.api.routes.ingestion.integrity_link import get_integrity_link

        session = _mock_session(_link())

        result = get_integrity_link(session, _owner_ctx(), INTLINK_ID, None)

        assert result is not None

    def test_returns_entity_for_write_group_user(self) -> None:
        """WRITE group access is sufficient for METADATA_WRITE endpoint."""
        from src.api.routes.ingestion.integrity_link import get_integrity_link

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        result = get_integrity_link(session, _write_ctx(), INTLINK_ID, ORG_UUID)

        assert result is not None

    def test_returns_entity_for_admin(self) -> None:
        """Admin bypasses all permission checks."""
        from src.api.routes.ingestion.integrity_link import get_integrity_link

        session = _mock_session(_link())

        result = get_integrity_link(session, _admin_ctx(), INTLINK_ID, None)

        assert result is not None


# ────────────────────────────────────────────────────────
# GET /ingestion/integrity-link/{id}/rules  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestListIntegrityLinkRulesPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.integrity_link import list_integrity_link_rules

        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            list_integrity_link_rules(session, _ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_write_group_user(self) -> None:
        """WRITE group access is insufficient for OWNER_ONLY endpoint."""
        from src.api.routes.ingestion.integrity_link import list_integrity_link_rules

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        with pytest.raises(HTTPException) as exc_info:
            list_integrity_link_rules(session, _write_ctx(), INTLINK_ID, ORG_UUID)

        assert exc_info.value.status_code == 403

    def test_returns_rules_for_owner(self) -> None:
        from src.api.routes.ingestion.integrity_link import list_integrity_link_rules

        session = _mock_session(_link())

        result = list_integrity_link_rules(session, _owner_ctx(), INTLINK_ID, None)

        assert isinstance(result, list)


# ────────────────────────────────────────────────────────
# DELETE /ingestion/integrity-link/{id}/rules/{rule_id}  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestDeleteIntegrityLinkRulePermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.integrity_link import delete_integrity_link_rule

        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(session, _ctx(), INTLINK_ID, None, rule_id=1)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_write_group_user(self) -> None:
        """WRITE group access is insufficient for OWNER_ONLY endpoint."""
        from src.api.routes.ingestion.integrity_link import delete_integrity_link_rule

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(session, _write_ctx(), INTLINK_ID, ORG_UUID, rule_id=1)

        assert exc_info.value.status_code == 403


# ────────────────────────────────────────────────────────
# POST /ingestion/process/  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestProcessPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.process import process_staging_data
        from src.models.data_import import ProcessRequest

        session = _mock_session(_link())
        body = ProcessRequest(integrity_link_id=INTLINK_ID, title="Test")

        with pytest.raises(HTTPException) as exc_info:
            process_staging_data(
                body,
                session,
                _ctx(),
                None,
                sec_email="x@x.com",
                sec_firstname="X",
                sec_lastname="X",
            )

        assert exc_info.value.status_code == 403

    def test_returns_403_for_write_group_user(self) -> None:
        """WRITE group access is insufficient for OWNER_ONLY endpoint."""
        from src.api.routes.ingestion.process import process_staging_data
        from src.models.data_import import ProcessRequest

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)
        body = ProcessRequest(integrity_link_id=INTLINK_ID, title="Test")

        with pytest.raises(HTTPException) as exc_info:
            process_staging_data(
                body,
                session,
                _write_ctx(),
                ORG_UUID,
                sec_email="x@x.com",
                sec_firstname="X",
                sec_lastname="X",
            )

        assert exc_info.value.status_code == 403


# ────────────────────────────────────────────────────────
# GET /airflow/dags/{dag_id}/runs/{intlink_id}  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestAirflowDagRunByIntlinkPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.airflow import get_dag_run_by_intlink

        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _ctx(), None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_write_group_user(self) -> None:
        """WRITE group access is insufficient for OWNER_ONLY endpoint."""
        from src.api.routes.airflow import get_dag_run_by_intlink

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        with pytest.raises(HTTPException) as exc_info:
            get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _write_ctx(), ORG_UUID)

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.airflow.get_dag_run_api")
    def test_returns_result_for_owner(self, mock_api: MagicMock) -> None:
        from src.api.routes.airflow import get_dag_run_by_intlink

        session = _mock_session(_link())
        mock_runs = MagicMock()
        mock_api.return_value.get_dag_runs.return_value = mock_runs

        result = get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _owner_ctx(), None)

        assert result is mock_runs


# ────────────────────────────────────────────────────────
# GeoNetwork proxy  (METADATA_WRITE when dataset UUID in path)
# ────────────────────────────────────────────────────────


class TestGeoNetworkProxyPermission:
    @pytest.fixture
    def mock_settings(self) -> MagicMock:
        settings = MagicMock()
        settings.GEONETWORK_URL = "http://gn.example.com/geonetwork"
        settings.GEONETWORK_USERNAME = "admin"
        settings.GEONETWORK_PASSWORD = "pass"
        return settings

    @pytest.mark.asyncio
    async def test_returns_403_for_unauthorized_user_on_dataset_path(self) -> None:
        from src.api.routes.geonetwork import proxy_geonetwork

        session = _mock_session(_link())
        path = f"srv/api/records/{INTLINK_UUID}"
        request = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await proxy_geonetwork(path, request, session, _ctx(), None)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_403_for_read_group_user_on_dataset_path(self) -> None:
        """READ group access is insufficient for METADATA_WRITE endpoint."""
        from src.api.routes.geonetwork import proxy_geonetwork

        session = _mock_session_with_rule(_link(), RuleValue.READ)
        path = f"srv/api/records/{INTLINK_UUID}"
        request = MagicMock()

        with pytest.raises(HTTPException) as exc_info:
            await proxy_geonetwork(path, request, session, _read_ctx(), ORG_UUID)

        assert exc_info.value.status_code == 403


# ────────────────────────────────────────────────────────
# PUT /ingestion/integrity-link/{id}/rules  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestUpsertIntegrityLinkRulePermission:
    def _body(self) -> UpsertRuleRequest:
        return UpsertRuleRequest(
            group_or_role="org_test",
            rule_type=RuleType.METADATA,
            rule_value=RuleValue.WRITE,
        )

    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.integrity_link import upsert_integrity_link_rule

        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            upsert_integrity_link_rule(session, _ctx(), INTLINK_ID, None, self._body())

        assert exc_info.value.status_code == 403

    def test_returns_403_for_write_group_user(self) -> None:
        """WRITE group access is insufficient for OWNER_ONLY endpoint."""
        from src.api.routes.ingestion.integrity_link import upsert_integrity_link_rule

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        with pytest.raises(HTTPException) as exc_info:
            upsert_integrity_link_rule(session, _write_ctx(), INTLINK_ID, ORG_UUID, self._body())

        assert exc_info.value.status_code == 403

    def test_succeeds_for_owner(self) -> None:
        from src.api.routes.ingestion.integrity_link import upsert_integrity_link_rule

        session = _mock_session(_link())

        result = upsert_integrity_link_rule(session, _owner_ctx(), INTLINK_ID, None, self._body())

        assert result is not None


# ────────────────────────────────────────────────────────
# GET /ingestion/staging/{id}/metadata  (METADATA_WRITE)
# ────────────────────────────────────────────────────────


class TestGetStagingMetadataPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.staging import get_staging_metadata

        datakern_session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_staging_metadata(MagicMock(), datakern_session, _ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_read_group_user(self) -> None:
        """READ group access is insufficient for METADATA_WRITE endpoint."""
        from src.api.routes.ingestion.staging import get_staging_metadata

        datakern_session = _mock_session_with_rule(_link(), RuleValue.READ)

        with pytest.raises(HTTPException) as exc_info:
            get_staging_metadata(MagicMock(), datakern_session, _read_ctx(), INTLINK_ID, ORG_UUID)

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_requires_metadata_write_level(self, mock_load: MagicMock) -> None:
        """Verify endpoint passes AccessLevel.METADATA_WRITE (not OWNER_ONLY)."""
        from src.api.routes.ingestion.staging import get_staging_metadata

        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            get_staging_metadata(MagicMock(), MagicMock(), _ctx(), INTLINK_ID, None)

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.METADATA_WRITE, ANY, ANY, ANY)


# ────────────────────────────────────────────────────────
# PUT /ingestion/staging/{id}/metadata  (METADATA_WRITE)
# ────────────────────────────────────────────────────────


class TestPutStagingMetadataPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.staging import edit_staging_metadata

        datakern_session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            edit_staging_metadata(
                MagicMock(), datakern_session, _ctx(), INTLINK_ID, None, MagicMock()
            )

        assert exc_info.value.status_code == 403

    def test_returns_403_for_read_group_user(self) -> None:
        """READ group access is insufficient for METADATA_WRITE endpoint."""
        from src.api.routes.ingestion.staging import edit_staging_metadata

        datakern_session = _mock_session_with_rule(_link(), RuleValue.READ)

        with pytest.raises(HTTPException) as exc_info:
            edit_staging_metadata(
                MagicMock(), datakern_session, _read_ctx(), INTLINK_ID, ORG_UUID, MagicMock()
            )

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_requires_metadata_write_level(self, mock_load: MagicMock) -> None:
        """Verify endpoint passes AccessLevel.METADATA_WRITE (not OWNER_ONLY)."""
        from src.api.routes.ingestion.staging import edit_staging_metadata

        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            edit_staging_metadata(MagicMock(), MagicMock(), _ctx(), INTLINK_ID, None, MagicMock())

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.METADATA_WRITE, ANY, ANY, ANY)


# ────────────────────────────────────────────────────────
# GET /ingestion/staging/{id}/preview  (METADATA_WRITE)
# ────────────────────────────────────────────────────────


class TestGetStagingPreviewPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.staging import get_staging_preview

        datakern_session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_staging_preview(MagicMock(), datakern_session, _ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_read_group_user(self) -> None:
        """READ group access is insufficient for METADATA_WRITE endpoint."""
        from src.api.routes.ingestion.staging import get_staging_preview

        datakern_session = _mock_session_with_rule(_link(), RuleValue.READ)

        with pytest.raises(HTTPException) as exc_info:
            get_staging_preview(MagicMock(), datakern_session, _read_ctx(), INTLINK_ID, ORG_UUID)

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_requires_metadata_write_level(self, mock_load: MagicMock) -> None:
        """Verify endpoint passes AccessLevel.METADATA_WRITE (not OWNER_ONLY)."""
        from src.api.routes.ingestion.staging import get_staging_preview

        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            get_staging_preview(MagicMock(), MagicMock(), _ctx(), INTLINK_ID, None)

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.METADATA_WRITE, ANY, ANY, ANY)
