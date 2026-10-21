import os
from datetime import datetime, timezone
from urllib.parse import urlencode

from airflow import DAG
from airflow.providers.standard.operators.trigger_dagrun import TriggerDagRunOperator
from callback import _dag_success_callback
from utils import get_records_as_dicts, normalize_nan


def load_scheduled_integrity_links():
    # The joined dataset is only referenced by id: resolve its final table here, as
    # the backend does for manual runs. Access was checked when the join was saved.
    sql = """
        SELECT
            il.id::text,
            il.integrity_organization,
            il.data_id,
            il.metadata_id,
            il.integrity_title,
            il.staging_table_name,
            il.final_table_name,
            il.schedule,
            il.integrity_transformation,
            il.source_url,
            il.source_import_type,
            il.source_layer,
            il.source_protocol,
            il.source_password_encrypted,
            joined.integrity_organization AS join_organization,
            joined.final_table_name AS join_final_table_name
        FROM datafeeder.integrity_link il
        LEFT JOIN datafeeder.integrity_link joined
            ON joined.id::text = il.integrity_transformation -> 'join' ->> 'integrity_link_id'
        WHERE il.schedule NOTNULL AND il.schedule NOT LIKE ''
    """
    return get_records_as_dicts(sql)


def _build_callback_url(route: str, integrity_link_id: str, final_table_name: str) -> str:
    backend_url = os.environ.get("BACKEND_INTERNAL_URL", "http://datafeeder-backend:8000")
    params = urlencode(
        {"integrity_link_id": integrity_link_id, "final_table_name": final_table_name}
    )
    return f"{backend_url}{route}?{params}"


DEFAULT_DATA_SCHEMA = "data"


def _target_schema(organization: str | None) -> str:
    """Same as the backend get_data_schema(): USE_ORG_SCHEMA must match on both sides."""
    use_org_schema = os.environ.get("USE_ORG_SCHEMA", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    return organization.lower() if use_org_schema and organization else DEFAULT_DATA_SCHEMA


def _join_target(config) -> dict | None:
    """Final table of the joined dataset, or None: the run then fails if a join is configured."""
    if not config.get("join_final_table_name"):
        return None
    return {
        "table_schema": _target_schema(config.get("join_organization")),
        "table_name": config["join_final_table_name"],
    }


def create_dag(config):
    dag_id = f"ingestion_{config['id']}"
    # Start date is fixed in order to avoid to regenerate a new dag version at each dag-processing analysis.
    dag = DAG(
        dag_id=dag_id,
        start_date=datetime(2026, 5, 3, tzinfo=timezone.utc),
        schedule=config.get("schedule"),
        tags=[config.get("id", "")],
        catchup=False,
        # A run waits for its process_dag run; never let runs pile up on short schedules.
        max_active_runs=1,
        on_success_callback=_dag_success_callback,
    )

    # Use a templated runtime timestamp ({{ ts_nodash }}) instead of a parse-time timestamp to avoid multiple dag versioning.
    # Run-id format '<integrity_link_id>_<ts>' must stay in sync with the backend's
    # run-id conventions in apps/backend/src/core/run_ids.py (used for run
    # cancellation and history purge matching); this app cannot import that module.
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
                "target_schema": _target_schema(config.get("integrity_organization")),
                "integrity_transformation": config.get("integrity_transformation") or {},
                "join_target": _join_target(config),
                "encrypted_credentials": config.get("source_password_encrypted", None),
                "success_callback_url": _build_callback_url(
                    "/internal/ingestion/process/dag_success",
                    config["id"],
                    config["final_table_name"],
                ),
                "failure_callback_url": _build_callback_url(
                    "/internal/ingestion/process/dag_failure",
                    config["id"],
                    config["final_table_name"],
                ),
            },
            wait_for_completion=True,
            # Wait in the triggerer instead of holding a worker slot: otherwise waiting
            # triggers can occupy every slot and starve the process_dag tasks (deadlock).
            deferrable=True,
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
