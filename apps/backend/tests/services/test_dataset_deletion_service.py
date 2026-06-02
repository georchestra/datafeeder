from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from src.models.integrity_link import IntegrityLink
from src.services.dataset_deletion_service import DatasetDeletionService


def _make_link(
    *,
    schedule: str | None = None,
    final_table_name: str | None = "my_table",
    metadata_id: str | None = "uuid-meta-1",
) -> IntegrityLink:
    """Helper to build a minimal IntegrityLink for tests."""
    link = IntegrityLink(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        integrity_owner="testuser",
        integrity_organization="testorg",
        staging_table_name="staging_table",
        source_import_type="URL",  # type: ignore[arg-type]
    )
    link.schedule = schedule
    link.final_table_name = final_table_name
    link.metadata_id = metadata_id
    return link


@pytest.fixture(autouse=True)
def mock_cancel_runs():
    """delete_dataset cancels in-flight runs first; keep it mocked everywhere."""
    with patch("src.services.dataset_deletion_service.cancel_ingestion_dag") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_purge_runs():
    """delete_dataset purges the Airflow run history; keep it mocked everywhere."""
    with patch("src.services.dataset_deletion_service.purge_dataset_dag_runs") as mock:
        yield mock


@pytest.fixture
def geoserver_svc() -> MagicMock:
    svc = MagicMock()
    svc.delete_layer.return_value = None
    return svc


@pytest.fixture
def metadata_svc() -> MagicMock:
    svc = MagicMock()
    svc.delete_record.return_value = None
    return svc


@pytest.fixture
def deletion_service(geoserver_svc: MagicMock, metadata_svc: MagicMock) -> DatasetDeletionService:
    return DatasetDeletionService(
        geoserver_service=geoserver_svc,
        metadata_service=metadata_svc,
    )


class TestDatasetDeletionService:
    """Unit tests for DatasetDeletionService.delete_dataset()."""

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_happy_path_with_schedule(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        geoserver_svc: MagicMock,
        metadata_svc: MagicMock,
    ) -> None:
        """With schedule: DAG deleted, then all resources cleaned up, IntegrityLink deleted."""
        link = _make_link(schedule="@daily")
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table") as mock_table_cls:
            mock_table = MagicMock()
            mock_table_cls.return_value = mock_table

            deletion_service.delete_dataset(link, session)

        mock_delete_dag.assert_called_once_with("ingestion_00000000-0000-0000-0000-000000000001")
        geoserver_svc.delete_layer.assert_called_once_with(
            workspace_name="testorg",
            datastore_name="testorg_ds",
            layer_name="my_table",
        )
        geoserver_svc.delete_layer_acl.assert_called_once_with(
            workspace_name="testorg",
            layer_name="my_table",
        )
        assert mock_table.drop.call_count == 2  # final table + staging table
        metadata_svc.delete_record.assert_called_once_with("uuid-meta-1")
        session.delete.assert_called_once_with(link)
        session.commit.assert_called_once()

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_dag_deleted_even_without_schedule(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
    ) -> None:
        """Without schedule: DAG deletion is still attempted (stale DAGs from a
        previously cleared schedule must be removed; 404 is tolerated)."""
        link = _make_link(schedule=None)
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        mock_delete_dag.assert_called_once_with("ingestion_00000000-0000-0000-0000-000000000001")

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_dag_delete_failure_raises_and_skips_remaining_steps(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        geoserver_svc: MagicMock,
        metadata_svc: MagicMock,
    ) -> None:
        """DAG deletion failure raises exception and no further cleanup is performed."""
        link = _make_link(schedule="@daily")
        session = MagicMock()
        mock_delete_dag.side_effect = Exception("Airflow error")

        with pytest.raises(Exception, match="Airflow error"):
            deletion_service.delete_dataset(link, session)

        geoserver_svc.delete_layer.assert_not_called()
        metadata_svc.delete_record.assert_not_called()
        session.delete.assert_not_called()

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_dag_404_treated_as_success(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        geoserver_svc: MagicMock,
    ) -> None:
        """delete_dag() silently handles 404 — deletion continues normally."""
        # delete_dag already swallows 404 (NotFoundException) and returns None
        mock_delete_dag.return_value = None
        link = _make_link(schedule="@daily")
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        # All subsequent steps called despite 404 being suppressed inside delete_dag
        geoserver_svc.delete_layer.assert_called_once()
        session.delete.assert_called_once_with(link)

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_without_final_table_skips_geoserver_and_table_drop(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        geoserver_svc: MagicMock,
    ) -> None:
        """When final_table_name is None: GeoServer and final table drop are skipped."""
        link = _make_link(final_table_name=None, schedule=None)
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table") as mock_table_cls:
            mock_table = MagicMock()
            mock_table_cls.return_value = mock_table

            deletion_service.delete_dataset(link, session)

        geoserver_svc.delete_layer.assert_not_called()
        geoserver_svc.delete_layer_acl.assert_not_called()
        # Only staging table drop should be attempted (1 call)
        assert mock_table.drop.call_count == 1

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_table_drop_failure_is_best_effort(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        metadata_svc: MagicMock,
    ) -> None:
        """Table drop failure is logged and suppressed; remaining steps continue."""
        link = _make_link(schedule=None)
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table") as mock_table_cls:
            mock_table = MagicMock()
            mock_table.drop.side_effect = Exception("DB error")
            mock_table_cls.return_value = mock_table

            # Should not raise
            deletion_service.delete_dataset(link, session)

        # Metadata deletion and IntegrityLink deletion still happen
        metadata_svc.delete_record.assert_called_once()
        session.delete.assert_called_once_with(link)

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_without_metadata_id_skips_geonetwork(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        metadata_svc: MagicMock,
    ) -> None:
        """When metadata_id is None: GeoNetwork deletion is skipped."""
        link = _make_link(metadata_id=None)
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        metadata_svc.delete_record.assert_not_called()
        session.delete.assert_called_once_with(link)


class TestCancelInFlightRuns:
    """In-flight DAG runs are cancelled before any resource is removed."""

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_cancels_runs_for_the_dataset(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        mock_cancel_runs: MagicMock,
    ) -> None:
        link = _make_link()
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        mock_cancel_runs.assert_called_once_with("00000000-0000-0000-0000-000000000001")

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_cancel_failure_is_best_effort(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        mock_cancel_runs: MagicMock,
    ) -> None:
        """A cancellation failure (Airflow hiccup) must not abort the deletion."""
        mock_cancel_runs.side_effect = Exception("airflow down")
        link = _make_link()
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        session.delete.assert_called_once_with(link)


class TestPurgeRunHistory:
    """Airflow run history is purged before the IntegrityLink row is deleted."""

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_purges_run_history(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        mock_purge_runs: MagicMock,
    ) -> None:
        link = _make_link()
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        mock_purge_runs.assert_called_once_with("00000000-0000-0000-0000-000000000001")

    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_purge_failure_is_best_effort(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        deletion_service: DatasetDeletionService,
        mock_purge_runs: MagicMock,
    ) -> None:
        """A purge failure must not abort the row deletion."""
        mock_purge_runs.side_effect = Exception("airflow down")
        link = _make_link()
        session = MagicMock()

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        session.delete.assert_called_once_with(link)


class TestOrgResourceCleanup:
    """Shared org resources are cleaned up when the last dataset is removed."""

    @patch("src.services.dataset_deletion_service.get_data_schema", return_value="testorg")
    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_last_dataset_triggers_cleanup(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        mock_get_schema: MagicMock,
        deletion_service: DatasetDeletionService,
        geoserver_svc: MagicMock,
    ) -> None:
        link = _make_link()
        session = MagicMock()
        session.exec.return_value.first.return_value = None  # no dataset left for the org

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        geoserver_svc.delete_datastore_if_empty.assert_called_once_with("testorg", "testorg_ds")
        geoserver_svc.delete_workspace_if_empty.assert_called_once_with("testorg")
        # Org schema drop attempted (RESTRICT — harmless when not empty)
        mock_data_engine.connect.assert_called()

    @patch("src.services.dataset_deletion_service.get_data_schema", return_value="testorg")
    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_remaining_datasets_skip_cleanup(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        mock_get_schema: MagicMock,
        deletion_service: DatasetDeletionService,
        geoserver_svc: MagicMock,
    ) -> None:
        link = _make_link()
        session = MagicMock()
        session.exec.return_value.first.return_value = MagicMock()  # another dataset remains

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        geoserver_svc.delete_datastore_if_empty.assert_not_called()
        geoserver_svc.delete_workspace_if_empty.assert_not_called()

    @patch("src.services.dataset_deletion_service.get_data_schema", return_value="data")
    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_shared_data_schema_is_never_dropped(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        mock_get_schema: MagicMock,
        deletion_service: DatasetDeletionService,
        geoserver_svc: MagicMock,
    ) -> None:
        """USE_ORG_SCHEMA=False → schema is the shared 'data' schema: never drop
        it; GeoServer workspace/datastore cleanup still applies."""
        link = _make_link()
        session = MagicMock()
        session.exec.return_value.first.return_value = None

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)

        geoserver_svc.delete_workspace_if_empty.assert_called_once_with("testorg")
        mock_data_engine.connect.assert_not_called()

    @patch("src.services.dataset_deletion_service.get_data_schema", return_value="testorg")
    @patch("src.services.dataset_deletion_service.data_engine")
    @patch("src.services.dataset_deletion_service.delete_dag")
    def test_cleanup_failure_is_best_effort(
        self,
        mock_delete_dag: MagicMock,
        mock_data_engine: MagicMock,
        mock_get_schema: MagicMock,
        deletion_service: DatasetDeletionService,
        geoserver_svc: MagicMock,
    ) -> None:
        """RESTRICT refusal (schema not empty) must not raise; row already deleted."""
        link = _make_link()
        session = MagicMock()
        session.exec.return_value.first.return_value = None
        mock_data_engine.connect.side_effect = Exception("schema not empty")

        with patch("src.services.dataset_deletion_service.Table"):
            deletion_service.delete_dataset(link, session)  # must not raise

        session.delete.assert_called_once_with(link)
