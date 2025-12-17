from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.dag_run_collection_response import DAGRunCollectionResponse
from airflow_client.client.models.dag_run_state import DagRunState
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ...services.airflow_client import get_dag_run_api
from ...services.airflow_logs import generate_failed_dag_run_logs

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


@router.get("/dags/{dag_id}/runs/{dag_run_id}/status", response_model=DagRunState)
def get_dag_run_status(dag_id: str, dag_run_id: str) -> DagRunState:
    try:
        dag_run = get_dag_run_api().get_dag_run(dag_id, dag_run_id)
        return dag_run.state
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"DAG run not found: {dag_id}/{dag_run_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.get("/dags/{dag_id}/runs/{dag_run_id}/logs", response_class=PlainTextResponse)
def get_dag_run_logs(dag_id: str, dag_run_id: str) -> str:
    return generate_failed_dag_run_logs(dag_id, dag_run_id)
