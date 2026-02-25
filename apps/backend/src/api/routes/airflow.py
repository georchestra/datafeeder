from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.dag_run_collection_response import DAGRunCollectionResponse
from airflow_client.client.models.dag_run_state import DagRunState
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from ...core.deps import DatakernSessionDep
from ...core.security import AccessLevel, load_authorized_integrity_link
from ...services.airflow_client import get_dag_run_api
from ...services.airflow_logs import generate_failed_dag_run_logs
from ...services.georchestra import GeorchestraContextDep

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


@router.get("/dags/{dag_id}/runs/{intlink_id}")
def get_dag_run_by_intlink(
    dag_id: str,
    intlink_id: str,
    session: DatakernSessionDep,
    geo_ctx: GeorchestraContextDep,
    limit: int = 20,
) -> DAGRunCollectionResponse:
    load_authorized_integrity_link(intlink_id, AccessLevel.OWNER_ONLY, geo_ctx, session)
    try:
        dag_runs = get_dag_run_api().get_dag_runs(dag_id, run_id_pattern=f"{intlink_id}_%")
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
