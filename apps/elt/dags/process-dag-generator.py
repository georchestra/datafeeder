import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from airflow import DAG
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from utils import get_datafeeder_pg_hook, normalize_nan


def load_scheduled_integrity_links():
    sql = """
        SELECT
            id::text,
            data_id,
            metadata_id,
            integrity_title,
            staging_table_name,
            final_table_name,
            schedule,
            integrity_transformation,
            source_url,
            source_import_type,
            source_layer,
            source_protocol,
            source_password_encrypted
        FROM datafeeder.integrity_link
        WHERE schedule NOTNULL AND schedule NOT LIKE ''
    """
    return get_datafeeder_pg_hook().get_pandas_df(sql).to_dict(orient="records")


def _build_callback_url(route: str, integrity_link_id: str, final_table_name: str) -> str:
    backend_url = os.environ.get("BACKEND_INTERNAL_URL", "http://datafeeder-backend:8000")
    params = urlencode(
        {"integrity_link_id": integrity_link_id, "final_table_name": final_table_name}
    )
    return f"{backend_url}{route}?{params}"


def create_dag(config):
    dag_id = f"ingestion_{config['id']}"
    # Start date is fixed in order to avoid to regenerate a new dag version at each dag-processing analysis.
    dag = DAG(
        dag_id=dag_id,
        start_date=datetime(2026, 5, 3, tzinfo=timezone.utc),
        schedule=config.get("schedule"),
        tags=[config.get("id", "")],
        catchup=False,
    )

    # Use a templated runtime timestamp ({{ ts_nodash }}) instead of a parse-time timestamp to avoid multiple dag versioning.
    dag_run_id = f"{config.get('id')}" + "_{{ ts_nodash }}"
    with dag:
        TriggerDagRunOperator(
            task_id="trigger_process_dag",
            trigger_dag_id="process_dag",
            trigger_run_id=dag_run_id,
            conf={
                "source": config.get("source_url"),
                "source_type": config.get("source_import_type").upper(),
                "source_layer": normalize_nan(config.get("source_layer"), ""),
                "source_protocol": normalize_nan(config.get("source_protocol"), ""),
                "final_table_name": config.get("final_table_name"),
                "integrity_transformation": config.get("integrity_transformation") or {},
                "encrypted_credentials": config.get("source_password_encrypted", None),
                "success_callback_url": _build_callback_url(
                    "/ingestion/process/dag_success",
                    config["id"],
                    config["final_table_name"],
                ),
                "failure_callback_url": _build_callback_url(
                    "/ingestion/process/dag_failure",
                    config["id"],
                    config["final_table_name"],
                ),
            },
            wait_for_completion=True,
            poke_interval=5,
        )

    return dag


# Create DAGs dynamically
configs = load_scheduled_integrity_links()
# Warning: Aiflow may throw psycopg2.errors.UndefinedTable: relation "datafeeder.integrity_link" does not exist
# if there's no scheduled integrity links.
for config in configs:
    dag_id = f"ingestion_{config['id']}"
    globals()[dag_id] = create_dag(config)
