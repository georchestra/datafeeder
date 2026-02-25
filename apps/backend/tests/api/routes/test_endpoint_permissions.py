"""Integration tests: verify each protected endpoint enforces permissions.

Each test class covers one protected endpoint, testing:
- 403 when the user has no matching access (no rules, not owner, not admin)
- Success (200/204) when the user is authorized (owner in these tests)
"""

from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from src.models.data_import import ImportType
from src.models.integrity_link import IntegrityLink
from src.services.georchestra import GeorchestraContext

INTLINK_ID = str(uuid4())
INTLINK_UUID = UUID(INTLINK_ID)


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


def _mock_session(link: IntegrityLink | None = None) -> MagicMock:
    """Session that returns *link* on `session.get(...)` and no rules."""
    session = MagicMock()
    session.get.return_value = link
    mock_exec = MagicMock()
    mock_exec.all.return_value = []  # no rules → no group access
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
            get_integrity_link(session, _ctx(), INTLINK_ID)

        assert exc_info.value.status_code == 403

    def test_returns_entity_for_owner(self) -> None:
        from src.api.routes.ingestion.integrity_link import get_integrity_link

        session = _mock_session(_link())

        result = get_integrity_link(session, _owner_ctx(), INTLINK_ID)

        assert result is not None


# ────────────────────────────────────────────────────────
# GET /ingestion/integrity-link/{id}/rules  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestListIntegrityLinkRulesPermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.integrity_link import list_integrity_link_rules

        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            list_integrity_link_rules(session, _ctx(), INTLINK_ID)

        assert exc_info.value.status_code == 403

    def test_returns_rules_for_owner(self) -> None:
        from src.api.routes.ingestion.integrity_link import list_integrity_link_rules

        session = _mock_session(_link())

        result = list_integrity_link_rules(session, _owner_ctx(), INTLINK_ID)

        assert isinstance(result, list)


# ────────────────────────────────────────────────────────
# DELETE /ingestion/integrity-link/{id}/rules/{rule_id}  (OWNER_ONLY)
# ────────────────────────────────────────────────────────


class TestDeleteIntegrityLinkRulePermission:
    def test_returns_403_for_unauthorized_user(self) -> None:
        from src.api.routes.ingestion.integrity_link import delete_integrity_link_rule

        session = _mock_session(_link())

        with pytest.raises(HTTPException) as exc_info:
            delete_integrity_link_rule(session, _ctx(), INTLINK_ID, rule_id=1)

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
            get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _ctx())

        assert exc_info.value.status_code == 403

    @patch("src.api.routes.airflow.get_dag_run_api")
    def test_returns_result_for_owner(self, mock_api: MagicMock) -> None:
        from src.api.routes.airflow import get_dag_run_by_intlink

        session = _mock_session(_link())
        mock_runs = MagicMock()
        mock_api.return_value.get_dag_runs.return_value = mock_runs

        result = get_dag_run_by_intlink("process_dag", INTLINK_ID, session, _owner_ctx())

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
            await proxy_geonetwork(path, request, session, _ctx())

        assert exc_info.value.status_code == 403
