import logging
from datetime import datetime
from typing import Any

from airflow.models import Param
from airflow.sdk import dag
from callback import _dag_failure_callback, _dag_success_callback
from data_manipulation.logging import configure_logging
from task_groups.ingestion import ingestion_group
from utils import get_staging_timeout

LOG_DIR = "/opt/airflow/logs"

logger = logging.getLogger(__name__)


@dag(
    dag_id="staging_dag",
    schedule=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    params={  # type: ignore[arg-type]
        "source": Param(
            default="/tmp/myfile.gpkg",
            type="string",
            description="Source path or URL",
            minLength=1,
        ),
        "source_type": Param(
            default="FILE",
            type="string",
            enum=["FILE", "URL", "FTP", "DATABASE", "API"],
            description="FTP, URL, OGC WFS, FILE, DATABASE, API",
        ),
        "staging_table_name": Param(
            default="my_table",
            type="string",
            description="Name of the staging table to create",
            minLength=1,
        ),
        "success_callback_url": Param(
            default="",
            type=["null", "string"],
            description="URL to call on success",
            minLength=1,
        ),
        "failure_callback_url": Param(
            default="",
            type=["null", "string"],
            description="URL to call on failure",
            minLength=1,
        ),
        "encrypted_credentials": Param(
            default=None,
            type=["null", "string"],
            description="Encrypted credentials (base64-encoded pgp_sym_encrypt result)",
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
    },
    dagrun_timeout=get_staging_timeout(),
    on_success_callback=_dag_success_callback,
    on_failure_callback=_dag_failure_callback,
)
def staging_dag(**context: dict[str, Any]) -> None:
    """Staging DAG for initial data ingestion."""
    configure_logging(logging.getLogger("airflow.task"))

    ingestion_group(group_id="initial_ingestion")()


staging_dag_instance = staging_dag()
