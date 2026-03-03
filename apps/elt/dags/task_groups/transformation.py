"""Final transformation task group."""

import logging
from typing import Any

from airflow.exceptions import AirflowException
from airflow.sdk import task, task_group
from airflow.utils.trigger_rule import TriggerRule
from data_manipulation import (
    IntegrityTransformation,
    apply_transformations,
    read_data_from_postgis,
    write_data_to_postgis,
)
from data_manipulation.logging import configure_logging
from sqlalchemy import MetaData, Table
from utils import get_data_sql_engine, get_final_schema, get_staging_schema

logger = logging.getLogger(__name__)
configure_logging(logger)


def process_transformation_group(
    group_id: str = "final_transformation",
    task_id_where_to_get_staging_table_name: str | None = None,
):
    """Factory function that returns a task group for final transformation.

    Args:
        group_id: Identifier for this task group instance
        task_id_where_to_get_staging_table_name: Task ID from which to pull staging_table_name via XCom.
            If None, staging_table_name must be provided in params.

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
            final_schema = get_final_schema()
            staging_schema = get_staging_schema()

            try:
                logger.info(f"Reading data from {staging_schema}.{staging_table_name}")
                data = read_data_from_postgis(
                    table_name=staging_table_name,
                    engine=engine,
                    schema=staging_schema,
                )
                logger.info(f"Successfully read {len(data)} rows from staging")

                logger.info(f"Applying transformations with config: {transformation_config}")
                transformed_data = apply_transformations(data, transformation_config)
                logger.info(f"Transformations applied to {len(transformed_data)} rows")

                logger.info(f"Writing data to {final_schema}.{final_table_name}")
                write_data_to_postgis(
                    data=transformed_data,
                    table_name=final_table_name,
                    engine=engine,
                    schema=final_schema,
                    create_id=True,
                )
                logger.info(f"Successfully wrote {len(transformed_data)} rows to final table")

            except Exception as e:
                raise AirflowException(f"Failed to transform and load data: {e}")

        @task(
            task_id="clean_staging_table_task",
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
