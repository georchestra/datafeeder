"""Process DAG for transforming data from staging into final table."""

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from airflow.exceptions import AirflowException
from airflow.models import Param
from airflow.sdk import dag, task
from callback import _dag_failure_callback, _dag_success_callback
from data_manipulation.logging import configure_logging
from task_groups.ingestion import ingestion_group
from task_groups.transformation import process_transformation_group

logger = logging.getLogger(__name__)


@dag(
    dag_id="process_dag",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    params={  # type: ignore[arg-type]
        # Either staging_table_name, for first ingestion mode
        "staging_table_name": Param(
            default=None,
            type=["null", "string"],
            description="Name of existing staging table (optional, if source and source_type provided)",
        ),
        # Or source + source_type for re-ingestion mode
        "source": Param(
            default=None,
            type=["null", "string"],
            description="Source path or URL for re-ingestion (optional, if staging_table_name provided)",
        ),
        "source_type": Param(
            default=None,
            type=["null", "string"],
            description="Type of source (FILE, URL, etc.) for re-ingestion (optional, if staging_table_name provided)",
            enum=[None, "API", "DATABASE", "FILE", "FTP", "URL"],
        ),
        "final_table_name": Param(
            default="",
            type="string",
            description="Name of the final table to create (required)",
            minLength=1,
        ),
        "integrity_transformation": Param(
            default={},
            type="object",
            description="JSON configuration for transformations (optional)",
        ),
        "success_callback_url": Param(
            default="",
            type=["null", "string"],
            description="URL to call on success (optional)",
            minLength=1,
        ),
        "failure_callback_url": Param(
            default="",
            type=["null", "string"],
            description="URL to call on failure (optional)",
            minLength=1,
        ),
        "encrypted_credentials": Param(
            default=None,
            type=["null", "string"],
            description="Encrypted credentials (base64-encoded pgp_sym_encrypt result)",
        ),
        "last_retrieval_timestamp": Param(
            default=None,
            type=["null", "string"],
            description="Timestamp of last retrieval (ISO format), indicates if this is a re-run (optional)",
        ),
        "source_layer": Param(
            default=None,
            type=["null", "string"],
            description="Layer/feature name for API/WFS import",
        ),
        "source_protocol": Param(
            default=None,
            type=["null", "string"],
            description="Service protocol for API import: 'wfs' or 'ogcFeatures'",
        ),
        "target_schema": Param(
            default="data",
            type="string",
            description="Target PostgreSQL schema for the final table (org-specific or 'data')",
            minLength=1,
        ),
    },
    on_success_callback=_dag_success_callback,
    on_failure_callback=_dag_failure_callback,
)
def process_dag(**context: dict[str, Any]) -> None:
    """DAG for final transformation and ingestion into final tables.

    Two modes:
    1. Use existing staging table: provide staging_table_name
    2. Re-ingest from source: provide source + source_type
    """
    configure_logging(logging.getLogger("airflow.task"))

    @task(task_id="generate_staging_table_name")
    def generate_staging_table_name(**context: dict[str, Any]) -> str:
        """Generate a temporary staging table name with UUID."""

        temp_staging_table = f"temp_{uuid4().hex[:8]}"
        logger.info(f"Generated temp staging table name: {temp_staging_table}")

        return temp_staging_table

    @task(task_id="use_staging_table_from_context")
    def use_staging_table_from_context(**context: dict[str, Any]) -> str:
        """Use the provided staging_table_name from params."""
        params = context.get("params", {})
        staging_table_name = params.get("staging_table_name")

        if not staging_table_name:
            raise AirflowException("staging_table_name must be provided in context")

        logger.info(f"Using staging table from context: {staging_table_name}")

        return staging_table_name

    @task.branch(task_id="decide_ingestion_mode")  # type: ignore[misc]
    def decide_ingestion_mode(**context: dict[str, Any]) -> str:
        """Decide whether to use existing staging or re-ingest from source."""
        params = context.get("params", {})
        staging_table_name = params.get("staging_table_name")
        source = params.get("source")
        source_type = params.get("source_type")

        # Validate that we have either staging_table_name OR (source + source_type)
        if staging_table_name:
            logger.info(f"Using existing staging table: {staging_table_name}")
            return "use_staging_table_from_context"
        elif source and source_type:
            logger.info("Re-ingesting from source")
            return "generate_staging_table_name"
        else:
            raise AirflowException(
                "Either staging_table_name OR (source + source_type) must be provided"
            )

    # Tasks
    branch = decide_ingestion_mode()
    use_staging = use_staging_table_from_context()
    generate_staging = generate_staging_table_name()

    # Ingestion group for refresh mode
    # Notes: Depends on generate_staging_table_name to access its XCom
    refresh_ingest = ingestion_group(group_id="refresh_ingestion")()

    # Two separate transformation groups - one for each path
    # Direct mode: will pull staging_table_name from use_staging_table_from_context XCom
    transform_direct = process_transformation_group(
        group_id="transform_direct",
        task_id_where_to_get_staging_table_name="use_staging_table_from_context",
    )()

    # Refresh mode: will pull staging_table_name from generate_staging_table_name XCom
    # clean_on_failure: the temp staging table must be dropped even when the
    # transform fails, otherwise every failed scheduled run leaks a temp_ table.
    transform_refresh = process_transformation_group(
        group_id="transform_refresh",
        task_id_where_to_get_staging_table_name="generate_staging_table_name",
        clean_on_failure=True,
    )()

    # Two branches from decision
    branch >> [use_staging, generate_staging]

    # Direct branch: use_staging_table_from_context then transform
    use_staging >> transform_direct

    # Refresh branch: generate_staging_table_name then ingest then transform
    generate_staging >> refresh_ingest >> transform_refresh


process_dag_instance = process_dag()
