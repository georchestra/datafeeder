from sqlalchemy import MetaData, Table
from sqlmodel import Session

from src.core.config import get_data_schema
from src.core.db import data_engine
from src.core.logging import get_logger
from src.models.integrity_link import IntegrityLink
from src.services.airflow_client import (
    cancel_ingestion_dag,
    delete_dag,
    purge_dataset_dag_runs,
)
from src.services.geoserver import GeoServerService
from src.services.metadata_service import MetadataService

logger = get_logger()


class DatasetDeletionService:
    """Orchestrates full deletion of a dataset and all associated resources."""

    def __init__(
        self,
        geoserver_service: GeoServerService,
        metadata_service: MetadataService,
    ):
        self.geoserver_service = geoserver_service
        self.metadata_service = metadata_service

    def delete_dataset(self, integrity_link: IntegrityLink, session: Session) -> None:
        """Delete a dataset and all associated resources.

        Cleanup sequence:
        0. Cancel in-flight DAG runs — best-effort
        1. Delete Airflow DAG — BLOCKING: raises on failure
        2. Delete GeoServer layer — best-effort
        3. Drop final data table — best-effort
        4. Drop staging table — best-effort
        5. Delete GeoNetwork record — best-effort
        6. Delete IntegrityLink from DB (cascades to IntegrityLinkRule)

        Args:
            integrity_link: The IntegrityLink to delete
            session: Datafeeder database session for deleting the IntegrityLink row

        Raises:
            Exception: If Airflow DAG deletion fails (other cleanup is skipped)
        """
        # Step 0: Cancel in-flight DAG runs for this dataset (best-effort) so a
        # run completing after deletion cannot recreate the staging/final table.
        try:
            cancel_ingestion_dag(str(integrity_link.id))
        except Exception as e:
            logger.warning(
                f"Failed to cancel in-flight DAG runs for IntegrityLink {integrity_link.id}: {e}",
                exc_info=True,
            )

        # Step 1: Delete Airflow DAG (blocking). Attempted even when no schedule
        # is currently set: a previously cleared schedule leaves a stale
        # ingestion_<id> DAG in Airflow, and delete_dag tolerates 404.
        dag_id = f"ingestion_{integrity_link.id}"
        try:
            delete_dag(dag_id)
            logger.info(f"Deleted Airflow DAG {dag_id}")
        except Exception as e:
            logger.error(f"Failed to delete Airflow DAG {dag_id}: {e}", exc_info=True)
            raise

        workspace_name = integrity_link.integrity_organization.lower()
        datastore_name = f"{workspace_name}_ds"

        # Step 2: Delete GeoServer layer and its ACL rules (best-effort)
        if integrity_link.final_table_name:
            self.geoserver_service.delete_layer(
                workspace_name=workspace_name,
                datastore_name=datastore_name,
                layer_name=integrity_link.final_table_name,
            )
            self.geoserver_service.delete_layer_acl(
                workspace_name=workspace_name,
                layer_name=integrity_link.final_table_name,
            )

        # Step 3: Drop final data table (best-effort)
        if integrity_link.final_table_name:
            self._drop_table_safe(get_data_schema(workspace_name), integrity_link.final_table_name)

        # Step 4: Drop staging table (best-effort)
        if integrity_link.staging_table_name:
            self._drop_table_safe("staging", integrity_link.staging_table_name)

        # Step 5: Delete GeoNetwork record (best-effort)
        if integrity_link.metadata_id:
            self.metadata_service.delete_record(integrity_link.metadata_id)

        # Step 5b: Purge Airflow run history (dag runs, task instances, XComs)
        # for this dataset (best-effort). Failed-run log files on the Airflow
        # volume are out of reach from the backend and are not removed.
        try:
            purge_dataset_dag_runs(str(integrity_link.id))
        except Exception as e:
            logger.warning(
                f"Failed to purge Airflow run history for IntegrityLink {integrity_link.id}: {e}",
                exc_info=True,
            )

        # Step 6: Delete IntegrityLink from DB (ON DELETE CASCADE removes IntegrityLinkRule rows)
        session.delete(integrity_link)
        session.commit()
        logger.info(f"Deleted IntegrityLink {integrity_link.id}")

    def _drop_table_safe(self, schema: str, table_name: str) -> None:
        """Drop a table in the given schema; log and suppress any errors."""
        try:
            metadata = MetaData(schema=schema)
            table = Table(table_name, metadata)
            table.drop(data_engine, checkfirst=True)
            logger.info(f"Dropped table {schema}.{table_name}")
        except Exception as e:
            logger.error(f"Failed to drop table {schema}.{table_name}: {e}", exc_info=True)
