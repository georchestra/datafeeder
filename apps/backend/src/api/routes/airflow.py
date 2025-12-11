from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.dag_run_state import DagRunState
from airflow_client.client.models.dag_run_collection_response import DAGRunCollectionResponse
from airflow_client.client.models.event_log_collection_response import EventLogCollectionResponse
from fastapi import APIRouter, HTTPException

from ...services.airflow_client import get_dag_run_api, get_event_log_api

router = APIRouter(prefix="/airflow", tags=["Airflow"])


@router.get("/dags/{dag_id}/runs")
def get_dag_runs(dag_id: str, limit: int = 20) -> DAGRunCollectionResponse:
    try:
        dag_runs = get_dag_run_api().get_dag_runs(dag_id, limit=limit, order_by=["-start_date"])
        return dag_runs
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"DAG not found: {dag_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.get("/dags/{dag_id}/runs/{dag_run_id}", response_model=DagRunState)
def get_dag_run_status(dag_id: str, dag_run_id: str) -> DagRunState:
    try:
        dag_run = get_dag_run_api().get_dag_run(dag_id, dag_run_id)
        return dag_run.state
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"DAG run not found: {dag_id}/{dag_run_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.get("/dags/{dag_id}/runs/{dag_run_id}/logs")
def get_dag_run_logs(dag_id: str, dag_run_id: str) -> EventLogCollectionResponse:
    try:
        dag_run_logs = get_event_log_api().get_event_logs(dag_id=dag_id, run_id=dag_run_id)
        return dag_run_logs
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"Logs not found for DAG run: {dag_id}/{dag_run_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")
