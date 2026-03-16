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

from airflow_client.client.models.dag_run_state import DagRunState

from src.api.routes.airflow import get_dag_run_by_intlink, get_dag_run_logs, get_dag_run_status
from src.api.routes.ingestion.integrity_link import (
    delete_integrity_link,
    delete_integrity_link_rule,
    get_integrity_link,
    list_integrity_link_rules,
    upsert_integrity_link_rule,
)
from src.api.routes.ingestion.process import process_staging_data
from src.api.routes.ingestion.staging import (
    edit_staging_metadata,
    get_staging_metadata,
    get_staging_preview,
)
from src.core.security import AccessLevel, EffectiveAccess
from src.models.data_import import ImportType, ProcessRequest
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


def _mock_session(link: IntegrityLink | None = None, access_result: str | None = None) -> MagicMock:
    """Session that returns *link* on `session.get(...)` and *access_result* from exec().first()."""
    session = MagicMock()
    session.get.return_value = link
    mock_exec = MagicMock()
    mock_exec.first.return_value = access_result
    mock_exec.all.return_value = []
    session.exec.return_value = mock_exec
    return session


def _mock_session_with_rule(link: IntegrityLink, rule_value: RuleValue) -> MagicMock:
    """Session that returns *link* and the corresponding access level from exec().first()."""
    access = (
        EffectiveAccess.WRITE.value if rule_value == RuleValue.WRITE else EffectiveAccess.READ.value
    )
    session = MagicMock()
    session.get.return_value = link
    mock_exec = MagicMock()
    mock_exec.first.return_value = access
    mock_exec.all.return_value = []
    session.exec.return_value = mock_exec
    return session


# ────────────────────────────────────────────────────────
# GET /ingestion/integrity-link/{id}  (METADATA_WRITE)
# ────────────────────────────────────────────────────────


class TestGetIntegrityLinkPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_integrity_link(session, _ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_read_group_user(self) -> None:
        """READ group access is insufficient for METADATA_WRITE endpoint."""

        session = _mock_session_with_rule(_link(), RuleValue.READ)

        with pytest.raises(HTTPException) as exc_info:
            get_integrity_link(session, _read_ctx(), INTLINK_ID, ORG_UUID)

        assert exc_info.value.status_code == 403

    def test_returns_entity_for_owner(self) -> None:
        session = _mock_session(_link(), access_result="OWNER")

        result = get_integrity_link(session, _owner_ctx(), INTLINK_ID, None)

        assert result is not None

    def test_returns_entity_for_write_group_user(self) -> None:
        """WRITE group access is sufficient for METADATA_WRITE endpoint."""

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        result = get_integrity_link(session, _write_ctx(), INTLINK_ID, ORG_UUID)

        assert result is not None

    def test_returns_entity_for_admin(self) -> None:
        """Admin bypasses all permission checks."""

        session = _mock_session(_link(), access_result="ADMIN")

        result = get_integrity_link(session, _admin_ctx(), INTLINK_ID, None)

        assert result is not None


# ────────────────────────────────────────────────────────
# GET /ingestion/integrity-link/{id}/rules  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestListIntegrityLinkRulesPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            list_integrity_link_rules(session, _ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_write_group_user(self) -> None:
        """WRITE group access is insufficient for OWNER_ONLY endpoint."""

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        with pytest.raises(HTTPException) as exc_info:
            list_integrity_link_rules(session, _write_ctx(), INTLINK_ID, ORG_UUID)

        assert exc_info.value.status_code == 403

    def test_returns_rules_for_owner(self) -> None:
        session = _mock_session(_link(), access_result="OWNER")

        result = list_integrity_link_rules(session, _owner_ctx(), INTLINK_ID, None)

        assert isinstance(result, list)


# ────────────────────────────────────────────────────────
# DELETE /ingestion/integrity-link/{id}/rules/{rule_id}  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestDeleteIntegrityLinkRulePermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(session, _ctx(), INTLINK_ID, None, rule_id=1)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_write_group_user(self) -> None:
        """WRITE group access is insufficient for OWNER_ONLY endpoint."""

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(session, _write_ctx(), INTLINK_ID, ORG_UUID, rule_id=1)

        assert exc_info.value.status_code == 403


# ────────────────────────────────────────────────────────
# POST /ingestion/process/  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestProcessPermission:
    @pytest.mark.asyncio
    async def test_returns_403_for_unauthorized_user(self) -> None:
        session = _mock_session(_link())
        body = ProcessRequest(integrity_link_id=INTLINK_ID, title="Test")

        with pytest.raises(HTTPException) as exc_info:
            process_staging_data(
                body,
                session,
                _ctx(),
                None,
                MagicMock(),
                sec_email="x@x.com",
                sec_firstname="X",
                sec_lastname="X",
            )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_403_for_write_group_user(self) -> None:
        """WRITE group access is insufficient for OWNER_ONLY endpoint."""

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)
        body = ProcessRequest(integrity_link_id=INTLINK_ID, title="Test")

        with pytest.raises(HTTPException) as exc_info:
            process_staging_data(
                body,
                session,
                _write_ctx(),
                ORG_UUID,
                MagicMock(),
                sec_email="x@x.com",
                sec_firstname="X",
                sec_lastname="X",
            )

        assert exc_info.value.status_code == 403


# ────────────────────────────────────────────────────────
# GET /airflow/dags/{dag_id}/runs/{intlink_id}  (METADATA_READ)
# ────────────────────────────────────────────────────────

DAG_RUN_ID = f"{INTLINK_ID}_run_20260305"  # UUID has no underscores; split("_")[0] == INTLINK_ID


class TestAirflowDagRunByIntlinkPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _ctx(), None)

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.airflow.get_dag_run_api")
    def test_returns_result_for_read_group_user(self, mock_api: MagicMock) -> None:
        """READ group access is sufficient for METADATA_READ endpoint."""

        session = _mock_session_with_rule(_link(), RuleValue.READ)
        mock_api.return_value.get_dag_runs.return_value = MagicMock()

        result = get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _read_ctx(), ORG_UUID)

        assert result is not None

    @patch("src.api.routes.airflow.get_dag_run_api")
    def test_returns_result_for_write_group_user(self, mock_api: MagicMock) -> None:
        """WRITE group access is sufficient for METADATA_READ endpoint."""

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)
        mock_api.return_value.get_dag_runs.return_value = MagicMock()

        result = get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _write_ctx(), ORG_UUID)

        assert result is not None

    @patch("src.api.routes.airflow.get_dag_run_api")
    def test_returns_result_for_owner(self, mock_api: MagicMock) -> None:
        session = _mock_session(_link(), access_result="OWNER")
        mock_runs = MagicMock()
        mock_api.return_value.get_dag_runs.return_value = mock_runs

        result = get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _owner_ctx(), None)

        assert result is mock_runs

    @patch("src.api.routes.airflow.get_dag_run_api")
    def test_returns_result_for_admin(self, mock_api: MagicMock) -> None:
        """Admin bypasses all permission checks."""

        session = _mock_session(_link(), access_result="ADMIN")
        mock_api.return_value.get_dag_runs.return_value = MagicMock()

        result = get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _admin_ctx(), None)

        assert result is not None

    @patch("src.api.routes.airflow.load_authorized_integrity_link")
    def test_requires_metadata_read_level(self, mock_load: MagicMock) -> None:
        """Verify the endpoint enforces AccessLevel.METADATA_READ (not OWNER_ONLY)."""

        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            get_dag_run_by_intlink("process_dag", INTLINK_ID, MagicMock(), _ctx(), None)

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.METADATA_READ, ANY, ANY, ANY)


# ────────────────────────────────────────────────────────
# GET /airflow/dags/{dag_id}/runs/{dag_run_id}/status  (METADATA_READ)
# ────────────────────────────────────────────────────────


class TestAirflowDagRunStatusPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_dag_run_status("process_dag", DAG_RUN_ID, session, _ctx(), None)

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.airflow.get_task_executor")
    def test_returns_result_for_read_group_user(self, mock_executor: MagicMock) -> None:
        session = _mock_session_with_rule(_link(), RuleValue.READ)
        mock_executor.return_value.get_task_status.return_value.status = MagicMock()

        result = get_dag_run_status("process_dag", DAG_RUN_ID, session, _read_ctx(), ORG_UUID)

        assert result is not None

    @patch("src.api.routes.airflow.get_task_executor")
    def test_returns_result_for_owner(self, mock_executor: MagicMock) -> None:
        session = _mock_session(_link(), access_result="OWNER")
        mock_status = MagicMock()
        mock_executor.return_value.get_task_status.return_value.status = mock_status

        result = get_dag_run_status("process_dag", DAG_RUN_ID, session, _owner_ctx(), None)

        assert result is mock_status

    @patch("src.api.routes.airflow.get_task_executor")
    def test_returns_result_for_admin(self, mock_executor: MagicMock) -> None:
        session = _mock_session(_link(), access_result="ADMIN")
        mock_executor.return_value.get_task_status.return_value.status = MagicMock()

        result = get_dag_run_status("process_dag", DAG_RUN_ID, session, _admin_ctx(), None)

        assert result is not None

    @patch("src.api.routes.airflow.load_authorized_integrity_link")
    def test_extracts_intlink_id_from_dag_run_id(self, mock_load: MagicMock) -> None:
        """Verify intlink_id is extracted as the UUID prefix before the first underscore."""

        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            get_dag_run_status("process_dag", DAG_RUN_ID, MagicMock(), _ctx(), None)

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.METADATA_READ, ANY, ANY, ANY)


# ────────────────────────────────────────────────────────
# GET /airflow/dags/{dag_id}/runs/{dag_run_id}/logs  (METADATA_READ)
# ────────────────────────────────────────────────────────


class TestAirflowDagRunLogsPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_dag_run_logs("process_dag", DAG_RUN_ID, session, _ctx(), None)

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.airflow.get_task_executor")
    def test_returns_result_for_read_group_user(self, mock_executor: MagicMock) -> None:
        session = _mock_session_with_rule(_link(), RuleValue.READ)
        mock_executor.return_value.get_task_logs.return_value = "some log output"

        result = get_dag_run_logs("process_dag", DAG_RUN_ID, session, _read_ctx(), ORG_UUID)

        assert result == "some log output"

    @patch("src.api.routes.airflow.get_task_executor")
    def test_returns_result_for_owner(self, mock_executor: MagicMock) -> None:
        session = _mock_session(_link(), access_result="OWNER")
        mock_executor.return_value.get_task_logs.return_value = "some log output"

        result = get_dag_run_logs("process_dag", DAG_RUN_ID, session, _owner_ctx(), None)

        assert result == "some log output"

    @patch("src.api.routes.airflow.get_task_executor")
    def test_returns_result_for_admin(self, mock_executor: MagicMock) -> None:
        session = _mock_session(_link(), access_result="ADMIN")
        mock_executor.return_value.get_task_logs.return_value = "some log output"

        result = get_dag_run_logs("process_dag", DAG_RUN_ID, session, _admin_ctx(), None)

        assert result == "some log output"

    @patch("src.api.routes.airflow.load_authorized_integrity_link")
    def test_extracts_intlink_id_from_dag_run_id(self, mock_load: MagicMock) -> None:
        """Verify intlink_id is extracted as the UUID prefix before the first underscore."""

        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            get_dag_run_logs("process_dag", DAG_RUN_ID, MagicMock(), _ctx(), None)

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.METADATA_READ, ANY, ANY, ANY)


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
        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            upsert_integrity_link_rule(session, _ctx(), INTLINK_ID, None, self._body())

        assert exc_info.value.status_code == 403

    def test_returns_403_for_write_group_user(self) -> None:
        """WRITE group access is insufficient for OWNER_ONLY endpoint."""

        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        with pytest.raises(HTTPException) as exc_info:
            upsert_integrity_link_rule(session, _write_ctx(), INTLINK_ID, ORG_UUID, self._body())

        assert exc_info.value.status_code == 403

    def test_succeeds_for_owner(self) -> None:
        session = _mock_session(_link())
        access_mock = MagicMock()
        access_mock.first.return_value = "OWNER"
        no_rule_mock = MagicMock()
        no_rule_mock.first.return_value = None
        session.exec.side_effect = [access_mock, no_rule_mock]

        result = upsert_integrity_link_rule(session, _owner_ctx(), INTLINK_ID, None, self._body())

        assert result is not None


# ────────────────────────────────────────────────────────
# GET /ingestion/staging/{id}/metadata  (METADATA_WRITE)
# ────────────────────────────────────────────────────────


class TestGetStagingMetadataPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        datafeeder_session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_staging_metadata(MagicMock(), datafeeder_session, _ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_read_group_user(self) -> None:
        """READ group access is insufficient for METADATA_WRITE endpoint."""

        datafeeder_session = _mock_session_with_rule(_link(), RuleValue.READ)

        with pytest.raises(HTTPException) as exc_info:
            get_staging_metadata(MagicMock(), datafeeder_session, _read_ctx(), INTLINK_ID, ORG_UUID)

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_requires_metadata_write_level(self, mock_load: MagicMock) -> None:
        """Verify endpoint passes AccessLevel.METADATA_WRITE (not OWNER_ONLY)."""

        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            get_staging_metadata(MagicMock(), MagicMock(), _ctx(), INTLINK_ID, None)

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.METADATA_WRITE, ANY, ANY, ANY)


# ────────────────────────────────────────────────────────
# PUT /ingestion/staging/{id}/metadata  (METADATA_WRITE)
# ────────────────────────────────────────────────────────


class TestPutStagingMetadataPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        datafeeder_session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            edit_staging_metadata(
                MagicMock(), datafeeder_session, _ctx(), INTLINK_ID, None, MagicMock()
            )

        assert exc_info.value.status_code == 403

    def test_returns_403_for_read_group_user(self) -> None:
        """READ group access is insufficient for METADATA_WRITE endpoint."""

        datafeeder_session = _mock_session_with_rule(_link(), RuleValue.READ)

        with pytest.raises(HTTPException) as exc_info:
            edit_staging_metadata(
                MagicMock(), datafeeder_session, _read_ctx(), INTLINK_ID, ORG_UUID, MagicMock()
            )

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_requires_metadata_write_level(self, mock_load: MagicMock) -> None:
        """Verify endpoint passes AccessLevel.METADATA_WRITE (not OWNER_ONLY)."""

        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            edit_staging_metadata(MagicMock(), MagicMock(), _ctx(), INTLINK_ID, None, MagicMock())

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.METADATA_WRITE, ANY, ANY, ANY)


# ────────────────────────────────────────────────────────
# GET /ingestion/staging/{id}/preview  (METADATA_WRITE)
# ────────────────────────────────────────────────────────


class TestGetStagingPreviewPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        datafeeder_session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            get_staging_preview(MagicMock(), datafeeder_session, _ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_read_group_user(self) -> None:
        """READ group access is insufficient for METADATA_WRITE endpoint."""

        datafeeder_session = _mock_session_with_rule(_link(), RuleValue.READ)

        with pytest.raises(HTTPException) as exc_info:
            get_staging_preview(MagicMock(), datafeeder_session, _read_ctx(), INTLINK_ID, ORG_UUID)

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.ingestion.staging.load_authorized_integrity_link")
    def test_requires_metadata_write_level(self, mock_load: MagicMock) -> None:
        """Verify endpoint passes AccessLevel.METADATA_WRITE (not OWNER_ONLY)."""

        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            get_staging_preview(MagicMock(), MagicMock(), _ctx(), INTLINK_ID, None)

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.METADATA_WRITE, ANY, ANY, ANY)


# ────────────────────────────────────────────────────────
# DELETE /ingestion/integrity-link/{id}  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestDeleteIntegrityLinkPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link(session, _ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 403

    def test_returns_403_for_non_owner(self) -> None:
        """A writer (group rule) cannot delete — OWNER_ONLY endpoint."""
        session = _mock_session_with_rule(_link(), RuleValue.WRITE)

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link(session, _write_ctx(), INTLINK_ID, ORG_UUID)

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.ingestion.integrity_link.DatasetDeletionService")
    @patch("src.api.routes.ingestion.integrity_link.GeoServerService")
    @patch("src.api.routes.ingestion.integrity_link.MetadataService")
    @patch("src.api.routes.ingestion.integrity_link.get_settings")
    def test_returns_204_for_owner(
        self,
        mock_settings: MagicMock,
        mock_metadata_svc: MagicMock,
        mock_geoserver_svc: MagicMock,
        mock_deletion_svc_cls: MagicMock,
    ) -> None:
        """Owner can delete their own dataset."""
        session = _mock_session(_link(), access_result="OWNER")
        mock_deletion_svc = MagicMock()
        mock_deletion_svc_cls.return_value = mock_deletion_svc

        response = delete_integrity_link(session, _owner_ctx(), INTLINK_ID, None)

        assert response.status_code == 204
        mock_deletion_svc.delete_dataset.assert_called_once()

    @patch("src.api.routes.ingestion.integrity_link.DatasetDeletionService")
    @patch("src.api.routes.ingestion.integrity_link.GeoServerService")
    @patch("src.api.routes.ingestion.integrity_link.MetadataService")
    @patch("src.api.routes.ingestion.integrity_link.get_settings")
    def test_returns_204_for_admin(
        self,
        mock_settings: MagicMock,
        mock_metadata_svc: MagicMock,
        mock_geoserver_svc: MagicMock,
        mock_deletion_svc_cls: MagicMock,
    ) -> None:
        """Admin can delete any dataset."""
        session = _mock_session(_link(), access_result="ADMIN")
        mock_deletion_svc = MagicMock()
        mock_deletion_svc_cls.return_value = mock_deletion_svc

        response = delete_integrity_link(session, _admin_ctx(), INTLINK_ID, None)

        assert response.status_code == 204
        mock_deletion_svc.delete_dataset.assert_called_once()

    def test_returns_404_for_unknown_id(self) -> None:
        """Unknown integrity_link_id returns 404."""
        session = _mock_session(None)  # no link found

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link(session, _owner_ctx(), str(uuid4()), None)

        assert exc_info.value.status_code == 404

    @patch("src.api.routes.ingestion.integrity_link.DatasetDeletionService")
    @patch("src.api.routes.ingestion.integrity_link.GeoServerService")
    @patch("src.api.routes.ingestion.integrity_link.MetadataService")
    @patch("src.api.routes.ingestion.integrity_link.get_settings")
    def test_returns_500_on_dag_deletion_failure(
        self,
        mock_settings: MagicMock,
        mock_metadata_svc: MagicMock,
        mock_geoserver_svc: MagicMock,
        mock_deletion_svc_cls: MagicMock,
    ) -> None:
        """DAG deletion failure returns HTTP 500."""
        session = _mock_session(_link(), access_result="OWNER")
        mock_deletion_svc = MagicMock()
        mock_deletion_svc.delete_dataset.side_effect = Exception("Airflow error")
        mock_deletion_svc_cls.return_value = mock_deletion_svc

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link(session, _owner_ctx(), INTLINK_ID, None)

        assert exc_info.value.status_code == 500

    @patch("src.api.routes.ingestion.integrity_link.load_authorized_integrity_link")
    def test_requires_owner_only_access_level(self, mock_load: MagicMock) -> None:
        """Verify endpoint passes AccessLevel.OWNER_ONLY."""
        mock_load.side_effect = HTTPException(status_code=403)

        with pytest.raises(HTTPException):
            delete_integrity_link(MagicMock(), _ctx(), INTLINK_ID, None)

        mock_load.assert_called_once_with(INTLINK_ID, AccessLevel.OWNER_ONLY, ANY, ANY, ANY)
