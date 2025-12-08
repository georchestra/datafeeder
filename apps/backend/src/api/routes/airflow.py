from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.dag_run_state import DagRunState
from fastapi import APIRouter, HTTPException

from ...services.airflow_client import get_dag_run_api

router = APIRouter(prefix="/airflow", tags=["Airflow"])


@router.get("/dags/{dag_id}/runs/{dag_run_id}", tags=["Airflow"], response_model=DagRunState)
def get_dag_run_status(dag_id: str, dag_run_id: str) -> DagRunState:
    try:
        dag_run = get_dag_run_api().get_dag_run(dag_id, dag_run_id)
        return dag_run.state
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"DAG run not found: {dag_id}/{dag_run_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")
