"""Final transformation task group."""

import logging
from typing import Any

from airflow.exceptions import AirflowException
from airflow.sdk import task, task_group
from airflow.utils.trigger_rule import TriggerRule
from data_manipulation import (
    CHUNK_SIZE,
    IntegrityTransformation,
    read_and_transform_data,
    write_data_to_postgis,
)
from data_manipulation.database import create_schema
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
                # If this is a re-run (has last_retrieval_timestamp), drop the old final table first
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
                    f"Reading, transforming and writing data from "
                    f"{staging_schema}.{staging_table_name} to {final_schema}.{final_table_name}"
                )

                # Read, transform and write one chunk at a time to keep the memory footprint
                # low for large tables (mirrors the chunked ingestion in ingestion.py).
                i = 0
                total_rows = 0
                while True:
                    transformed_data = read_and_transform_data(
                        table_name=staging_table_name,
                        engine=engine,
                        schema=staging_schema,
                        config=transformation_config,
                        limit=CHUNK_SIZE,
                        offset=i * CHUNK_SIZE,
                    )
                    if transformed_data.empty:
                        break

                    chunk_len = len(transformed_data)
                    write_data_to_postgis(
                        data=transformed_data,
                        table_name=final_table_name,
                        engine=engine,
                        schema=final_schema,
                        # The UUID primary key is created once on the first chunk; subsequent
                        # appended rows receive their id_datafeeder from the column default.
                        create_id=i == 0,
                        if_exists="replace" if i == 0 else "append",
                    )
                    total_rows += chunk_len
                    logger.info(
                        f"Transformed and wrote chunk {i} ({chunk_len} rows) to final table"
                    )

                    # A short read means the staging table is exhausted — avoid an extra empty query.
                    if chunk_len < CHUNK_SIZE:
                        break
                    i += 1

                if total_rows == 0:
                    logger.error("No data to write after transformation.")
                    raise AirflowException("No data to write after transformation.")

                logger.info(f"Successfully wrote {total_rows} rows to final table")

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
