from datetime import datetime

from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from utils import get_datakern_pg_hook

from airflow import DAG


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
            schedule_enabled,
            integrity_transformation,
            source_url,
            source_import_type,
            source_password_encrypted,
            source_auth_enabled
        FROM datakern.integrity_link
        WHERE schedule_enabled = true
    """
    return get_datakern_pg_hook().get_pandas_df(sql).to_dict(orient="records")


def create_dag(config):
    dag_id = f"ingestion_{config['id']}"
    dag = DAG(
        dag_id=dag_id,
        start_date=datetime.now(),
        schedule=config.get("schedule"),
        tags=[config.get("id", "")],
        catchup=False,
    )

    with dag:
        TriggerDagRunOperator(
            task_id="trigger_process_dag",
            trigger_dag_id="process_dag",
            trigger_run_id=config.get("id", "") + "_{{ ts_nodash }}",
            conf={
                "source": config.get("source_url"),
                "source_type": config.get("source_import_type", "").upper(),
                "staging_table_name": config.get("staging_table_name"),
                "final_table_name": config.get("final_table_name"),
                "integrity_transformation": config.get("integrity_transformation", {}),
                "metadata_id": config.get("metadata_id"),
                "basic_auth_encrypted": config.get("source_password_encrypted", None),
                "success_callback_url": f"http://example.com/success/{config['id']}",
                "failure_callback_url": f"http://example.com/failure/{config['id']}",
            },
            wait_for_completion=True,
            poke_interval=15,
        )

    return dag


# Create DAGs dynamically
configs = load_scheduled_integrity_links()
for config in configs:
    dag_id = f"ingestion_{config['id']}"
    globals()[dag_id] = create_dag(config)
