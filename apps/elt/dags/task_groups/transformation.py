"""Final transformation task group."""

import logging
from typing import Any

from airflow.exceptions import AirflowException
from airflow.sdk import task, task_group
from airflow.utils.trigger_rule import TriggerRule
from data_manipulation import IntegrityTransformation
from data_manipulation.database import create_schema
from data_manipulation.transformation.transform_sql import transform_in_place_via_sql
from sqlalchemy import MetaData, Table
from utils import get_data_sql_engine, get_staging_schema

logger = logging.getLogger(__name__)


def process_transformation_group(
    group_id: str = "final_transformation",
    task_id_where_to_get_staging_table_name: str | None = None,
    clean_on_failure: bool = False,
):
    """Factory function that returns a task group for final transformation.

    Args:
        group_id: Identifier for this task group instance
        task_id_where_to_get_staging_table_name: Task ID from which to pull staging_table_name via XCom.
            If None, staging_table_name must be provided in params.
        clean_on_failure: When True, clean_staging_table_task runs even if the
            transform task failed (TriggerRule.ALL_DONE). Use for refresh mode,
            where the staging table is a throwaway temp table that would
            otherwise leak on failure. Keep False for direct mode so the user's
            tracked staging table survives a failed transform.

    Required params:
        - final_table_name: Name of the final table to write to
        - staging_table_name: Name of staging table (if not using XCom)
        - integrity_transformation: JSON config for transformations (optional, default: {})
    """

    @task_group(group_id=group_id)
    def _transformation_group():
        """Task group for final transformation from staging to final table."""

        @task(
            task_id="read_transform_write_task",
            trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
        )
        def read_transform_write_task(**context: dict[str, Any]) -> None:
            """Read from staging, apply transformations, and write to final table."""
            params = context.get("params", {})
            ti = context["ti"]

            final_table_name = params.get("final_table_name")
            transformation_dict: dict[str, Any] = params.get("integrity_transformation", {})
            transformation_config = IntegrityTransformation(**transformation_dict)

            logger.info(
                f"Final transformation with config: {transformation_dict} for {final_table_name}"
            )

            # Get staging_table_name from XCom or params
            staging_table_name = None
            if task_id_where_to_get_staging_table_name:
                staging_table_name = ti.xcom_pull(task_ids=task_id_where_to_get_staging_table_name)
                logger.info(
                    f"Using staging_table_name from task '{task_id_where_to_get_staging_table_name}': {staging_table_name}"
                )
            else:
                staging_table_name = params.get("staging_table_name")
                logger.info(f"Using staging_table_name from params: {staging_table_name}")

            # Validate required parameters
            if not staging_table_name or not staging_table_name.strip():
                raise AirflowException("staging_table_name is required and cannot be empty")

            if not final_table_name:
                raise AirflowException("final_table_name is required and cannot be empty")

            engine = get_data_sql_engine()
            final_schema = params.get("target_schema", "data")
            staging_schema = get_staging_schema()

            try:
                # If this is a re-run, drop the previous final table so the
                # CREATE TABLE … AS SELECT below has a clean target.
                last_retrieval_timestamp = params.get("last_retrieval_timestamp")
                if last_retrieval_timestamp:
                    try:
                        logger.info(
                            f"Re-run detected (last_retrieval_timestamp={last_retrieval_timestamp}). "
                            f"Dropping existing final table: {final_schema}.{final_table_name}"
                        )
                        with engine.connect() as conn:
                            metadata = MetaData(schema=final_schema)
                            table = Table(final_table_name, metadata)
                            table.drop(conn, checkfirst=True)
                            conn.commit()
                        logger.info(
                            f"Successfully dropped final table: {final_schema}.{final_table_name}"
                        )
                    except Exception as drop_error:
                        logger.warning(
                            f"Failed to drop final table {final_schema}.{final_table_name}: {drop_error}",
                            exc_info=True,
                        )

                create_schema(engine, final_schema)
                logger.info(
                    f"Running SQL transform {staging_schema}.{staging_table_name} "
                    f"→ {final_schema}.{final_table_name}"
                )
                row_count = transform_in_place_via_sql(
                    staging_table_name=staging_table_name,
                    staging_schema=staging_schema,
                    target_table_name=final_table_name,
                    target_schema=final_schema,
                    engine=engine,
                    config=transformation_config,
                    create_id=True,
                )
                if row_count == 0:
                    logger.error("No data to write after transformation.")
                    raise AirflowException("No data to write after transformation.")
                logger.info(f"Successfully wrote {row_count} rows to final table")

            except AirflowException:
                raise
            except Exception as e:
                raise AirflowException(f"Failed to transform and load data: {e}")

        @task(
            task_id="clean_staging_table_task",
            trigger_rule=TriggerRule.ALL_DONE if clean_on_failure else TriggerRule.ALL_SUCCESS,
        )
        def clean_staging_table_task(**context: dict[str, Any]) -> None:
            """Clean up staging table after transformation."""
            ti = context["ti"]

            # Get staging_table_name from XCom or params
            staging_table_name = None
            if task_id_where_to_get_staging_table_name:
                staging_table_name = ti.xcom_pull(task_ids=task_id_where_to_get_staging_table_name)
                logger.info(
                    f"Cleaning staging table from task '{task_id_where_to_get_staging_table_name}': {staging_table_name}"
                )

            if not staging_table_name or not staging_table_name.strip():
                logger.warning("staging_table_name is required to clean up, skipping cleanup")
                return

            engine = get_data_sql_engine()
            staging_schema = get_staging_schema()

            try:
                logger.info(f"Dropping staging table {staging_schema}.{staging_table_name}")
                schema = "staging"  # FIXME get it from config
                metadata = MetaData(schema=schema)
                t = Table(staging_table_name, metadata)
                t.drop(engine, checkfirst=True)
                logger.info("Staging table dropped successfully")
            except Exception as e:
                raise AirflowException(f"Failed to drop staging table: {e}")

        read_transform_write_task() >> clean_staging_table_task()

    return _transformation_group
