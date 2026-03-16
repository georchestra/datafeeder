"""Ingestion task group."""

import logging
from datetime import timedelta
from typing import Any, Literal

from airflow.exceptions import AirflowException
from airflow.sdk import Variable, task, task_group
from data_manipulation.constants import DB_URI_PREFIX
from data_manipulation.encryption import decrypt_credentials
from data_manipulation.ingestion import (
    ingest_data_from_database_into_postgis,
    ingest_data_from_file_into_postgis,
    ingest_data_from_ftp_into_postgis,
    ingest_data_from_url_into_postgis,
)
from data_manipulation.logging import configure_logging
from utils import (
    get_data_sql_engine,
    get_datafeeder_sql_engine,
    get_source_sql_engine,
    get_staging_schema,
    get_staging_timeout,
)

logger = logging.getLogger(__name__)
configure_logging(logger)


def ingestion_group(group_id: Literal["initial_ingestion", "refresh_ingestion"]):
    """Factory function that creates an ingestion task group.

    Args:
        group_id: Identifier for the task group (initial_ingestion or refresh_ingestion)

    Returns:
        A task group for data ingestion
    """

    @task_group(group_id=group_id)  # type: ignore[misc]
    def _ingestion_impl() -> None:
        """Task group for ingestion tasks.

        Tasks can access runtime configuration via context.
        """

        @task.branch(task_id="select_ingestion_mode")  # type: ignore[misc]
        def do_branching(**context: dict[str, Any]) -> str | bool:
            params = context.get("params", {})
            source_type = params.get("source_type")

            logger.info(f"Ingestion source_type: {source_type}")

            match source_type:
                case "FILE":
                    return f"{group_id}.file_ingest_step"
                case "URL":
                    return f"{group_id}.url_ingest_step"
                case "FTP":
                    return f"{group_id}.ftp_ingest_step"
                case "DATABASE":
                    return f"{group_id}.database_ingest_step"
                case _:
                    raise AirflowException(f"Unsupported source_type: {source_type}")

        @task(task_id="file_ingest_step", execution_timeout=timedelta(seconds=3600))
        def file_ingest_step(**context: dict[str, Any]) -> None:
            params = context.get("params", {})
            ti = context.get("ti")

            # Try to get staging_table_name from params first (staging_dag case)
            target_table_name = params.get("staging_table_name")

            # If not in params, try XCom from generate_staging_table_name (process_dag scheduled case)
            if not target_table_name and ti:
                target_table_name = ti.xcom_pull(task_ids="generate_staging_table_name")
                logger.info(f"Using staging_table_name from XCom: {target_table_name}")
            else:
                logger.info(f"Using staging_table_name from params: {target_table_name}")

            if not target_table_name:
                raise AirflowException("staging_table_name is not provided")

            engine = get_data_sql_engine()

            try:
                ingest_data_from_file_into_postgis(
                    params.get("source", ""),
                    target_table_name,
                    engine,
                    schema=get_staging_schema(),
                )
            except Exception as e:
                raise AirflowException(f"Failed to ingest data from file: {e}")

        @task(task_id="url_ingest_step")
        def url_ingest_step(**context: dict[str, Any]) -> None:
            params = context.get("params", {})
            ti = context.get("ti")

            # Try to get staging_table_name from params first (staging_dag case)
            target_table_name = params.get("staging_table_name")

            # If not in params, try XCom from generate_staging_table_name (process_dag scheduled case)
            if not target_table_name and ti:
                target_table_name = ti.xcom_pull(task_ids="generate_staging_table_name")
                logger.info(f"Using staging_table_name from XCom: {target_table_name}")
            else:
                logger.info(f"Using staging_table_name from params: {target_table_name}")

            if not target_table_name:
                raise AirflowException("staging_table_name is not provided")

            # Decrypt Basic Auth credentials if provided
            auth = None
            encrypted_credentials = params.get("encrypted_credentials")
            if encrypted_credentials:
                try:
                    encryption_key = Variable.get("datafeeder_encryption_key", default=None)
                    if not encryption_key:
                        raise AirflowException(
                            "Encryption key not found in Airflow Variables under 'datafeeder_encryption_key'"
                        )

                    engine = get_datafeeder_sql_engine()

                    with engine.connect() as conn:
                        username, password = decrypt_credentials(
                            conn, encrypted_credentials, encryption_key
                        )
                        auth = (username, password)
                        logger.info("Successfully decrypted Basic Auth credentials")
                except Exception as e:
                    logger.error(f"Failed to decrypt Basic Auth credentials: {e}")
                    raise AirflowException(f"Failed to decrypt credentials: {e}")

            engine = get_data_sql_engine()

            try:
                ingest_data_from_url_into_postgis(
                    params.get("source", ""),
                    target_table_name,
                    engine,
                    schema=get_staging_schema(),
                    auth=auth,
                )
            except Exception as e:
                raise AirflowException(f"Failed to ingest data from URL: {e}")

        @task(task_id="ftp_ingest_step", execution_timeout=get_staging_timeout())
        def ftp_ingest_step(**context: dict[str, Any]) -> None:
            params = context.get("params", {})
            ti = context.get("ti")

            # Try to get staging_table_name from params first (staging_dag case)
            target_table_name = params.get("staging_table_name")

            # If not in params, try XCom from generate_staging_table_name (process_dag scheduled case)
            if not target_table_name and ti:
                target_table_name = ti.xcom_pull(task_ids="generate_staging_table_name")
                logger.info(f"Using staging_table_name from XCom: {target_table_name}")
            else:
                logger.info(f"Using staging_table_name from params: {target_table_name}")

            if not target_table_name:
                raise AirflowException("staging_table_name is not provided")

            # Decrypt Ftp credentials if provided
            auth = None
            encrypted_credentials = params.get("encrypted_credentials")
            if encrypted_credentials:
                try:
                    encryption_key = Variable.get("datafeeder_encryption_key", default=None)
                    if not encryption_key:
                        raise AirflowException(
                            "Encryption key not found in Airflow Variables under 'datafeeder_encryption_key'"
                        )

                    engine = get_datafeeder_sql_engine()

                    with engine.connect() as conn:
                        username, password = decrypt_credentials(
                            conn, encrypted_credentials, encryption_key
                        )
                        auth = (username, password)
                        logger.info("Successfully decrypted Ftp credentials")
                except Exception as e:
                    logger.error(f"Failed to decrypt Ftp credentials: {e}")
                    raise AirflowException(f"Failed to decrypt credentials: {e}")

            try:
                engine = get_data_sql_engine()
                schema = get_staging_schema()

                ingest_data_from_ftp_into_postgis(
                    params.get("source", ""), target_table_name, engine, schema, auth
                )
            except Exception as e:
                raise AirflowException(f"Failed to ingest data from FTP: {e}")

        @task(task_id="database_ingest_step")
        def database_ingest_step(**context: dict[str, Any]) -> None:
            params = context.get("params", {})
            ti = context.get("ti")

            target_table_name = params.get("staging_table_name")

            if not target_table_name and ti:
                target_table_name = ti.xcom_pull(task_ids="generate_staging_table_name")
                logger.info(f"Using staging_table_name from XCom: {target_table_name}")
            else:
                logger.info(f"Using staging_table_name from params: {target_table_name}")

            if not target_table_name:
                raise AirflowException("staging_table_name is not provided")

            source = params.get("source", "")
            # Expected format: db://{db_key}/{schema}/{table}
            if not source.startswith(DB_URI_PREFIX):
                raise AirflowException(
                    f"Invalid database source URL format: '{source}'. Expected db://{{db_key}}/{{schema}}/{{table}}"
                )

            try:
                db_key, source_schema, source_table = source.removeprefix(DB_URI_PREFIX).split(
                    "/", 2
                )
            except ValueError:
                raise AirflowException(
                    f"Invalid database source URL format: '{source}'. Expected db://{{db_key}}/{{schema}}/{{table}}"
                )

            if not db_key or not source_schema or not source_table:
                raise AirflowException(
                    f"Invalid database source URL: db_key, schema, and table must all be non-empty (got '{source}')"
                )

            try:
                source_engine = get_source_sql_engine(db_key)
                target_engine = get_data_sql_engine()

                ingest_data_from_database_into_postgis(
                    source_schema=source_schema,
                    source_table=source_table,
                    source_engine=source_engine,
                    target_table=target_table_name,
                    target_engine=target_engine,
                    target_schema=get_staging_schema(),
                )
            except AirflowException:
                raise
            except Exception as e:
                raise AirflowException(f"Failed to ingest data from database {source}: {e}")

        do_branching() >> [
            file_ingest_step(),
            ftp_ingest_step(),
            url_ingest_step(),
            database_ingest_step(),
        ]

    return _ingestion_impl
