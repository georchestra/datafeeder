"""Final transformation task group."""

import logging
from typing import Any

from airflow.exceptions import AirflowException
from airflow.sdk import task, task_group
from data_manipulation import (
    apply_transformations,
    read_data_from_postgis,
    write_data_to_postgis,
)
from data_manipulation.logging import configure_logging
from utils import get_final_schema, get_sqlalchemy_engine, get_staging_schema

logger = logging.getLogger(__name__)
configure_logging(logger)


def final_transformation_group(
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

        @task(task_id="read_transform_write_task")
        def read_transform_write_task(**context: dict[str, Any]) -> None:
            """Read from staging, apply transformations, and write to final table."""
            params = context.get("params", {})
            ti = context["ti"]

            final_table_name = params.get("final_table_name")
            transformation_config = params.get("integrity_transformation", {})

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

            engine = get_sqlalchemy_engine()
            final_schema = get_final_schema()
            staging_schema = get_staging_schema()

            try:
                logger.info(f"Reading data from {staging_schema}.{staging_table_name}")
                gdf = read_data_from_postgis(
                    table_name=staging_table_name,
                    engine=engine,
                    schema=staging_schema,
                )
                logger.info(f"Successfully read {len(gdf)} rows from staging")

                logger.info(f"Applying transformations with config: {transformation_config}")
                transformed_gdf = apply_transformations(gdf, transformation_config)
                logger.info(f"Transformations applied to {len(transformed_gdf)} rows")

                logger.info(f"Writing data to {final_schema}.{final_table_name}")
                write_data_to_postgis(
                    gdf=transformed_gdf,
                    table_name=final_table_name,
                    engine=engine,
                    schema=final_schema,
                )
                logger.info(f"Successfully wrote {len(transformed_gdf)} rows to final table")

            except Exception as e:
                raise AirflowException(f"Failed to transform and load data: {e}")

        read_transform_write_task()

    return _transformation_group
