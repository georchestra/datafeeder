"""Final transformation task group."""

import logging
from typing import Any

from airflow.exceptions import AirflowException
from airflow.sdk import task, task_group
from data_manipulation import (
    read_data_from_postgis,
    apply_transformations,
    write_data_to_postgis,
)
from utils import get_final_schema, get_staging_schema, get_sqlalchemy_engine

logger = logging.getLogger(__name__)


@task_group(group_id="final_transformation")
def final_transformation_group() -> None:
    """Task group for final transformation from staging to final table.

    Required params:
        - staging_table_name: Name of the staging table to read from
        - final_table_name: Name of the final table to write to
        - integrity_transformation: JSON config for transformations (optional, default: {})

    Tasks can access runtime configuration via context.
    """

    @task(task_id="read_transform_write_task")
    def read_transform_write_task(**context: dict[str, Any]) -> None:
        """Read from staging, apply transformations, and write to final table."""
        params = context.get("params", {})
        staging_table_name = params.get("staging_table_name")
        final_table_name = params.get("final_table_name")
        transformation_config = params.get("integrity_transformation", {})

        # Validate required parameters
        if not staging_table_name:
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
                schema=final_schema
            )
            logger.info(f"Successfully wrote {len(transformed_gdf)} rows to final table")

        except Exception as e:
            raise AirflowException(f"Failed to transform and load data: {e}")

    read_transform_write_task()
