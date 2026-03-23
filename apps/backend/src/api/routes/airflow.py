import asyncio

from airflow_client.client.exceptions import NotFoundException
from airflow_client.client.models.dag_run_collection_response import DAGRunCollectionResponse
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from src.api.deps import DatafeederSessionDep, GeorchestraContextDep, OrgIdDep
from src.core.security import AccessLevel, load_authorized_integrity_link
from src.core.task_executor import TaskStatus
from src.services.airflow_client import get_dag_run_api
from src.services.executor_factory import get_task_executor

router = APIRouter(prefix="/airflow", tags=["Airflow"])

_NOTE_POLL_INTERVAL_S = 2
_NOTE_MAX_ATTEMPTS = 3


@router.get("/dags/{dag_id}/runs/{intlink_id}")
def get_dag_run_by_intlink(
    dag_id: str,
    intlink_id: str,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    org_id: OrgIdDep,
    limit: int = 20,
) -> DAGRunCollectionResponse:
    # Ensure the user has access to the integrity link associated with this DAG run
    load_authorized_integrity_link(intlink_id, AccessLevel.METADATA_READ, geo_ctx, session, org_id)

    try:
        dag_runs = get_dag_run_api().get_dag_runs(dag_id, run_id_pattern=f"{intlink_id}_%")
        return dag_runs
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"DAG not found: {dag_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.get("/dags/{dag_id}/runs/{dag_run_id}/status", response_model=TaskStatus)
def get_dag_run_status(
    dag_id: str,
    dag_run_id: str,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    org_id: OrgIdDep,
) -> TaskStatus:
    intlink_id = dag_run_id.split("_")[0]  # Extract intlink_id from run_id pattern
    # Ensure the user has access to the integrity link associated with this DAG run
    load_authorized_integrity_link(intlink_id, AccessLevel.METADATA_READ, geo_ctx, session, org_id)

    try:
        executor = get_task_executor()
        task_info = executor.get_task_status(dag_id, dag_run_id)
        return task_info.status
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"DAG run not found: {dag_id}/{dag_run_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.get("/dags/{dag_id}/runs/{dag_run_id}/note", response_model=str | None)
async def get_dag_run_note(
    dag_id: str,
    dag_run_id: str,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    org_id: OrgIdDep,
) -> str | None:
    """
    Return the note attached to a DAG run, but only if its value is ``"timed_out"``.

    This filter is a security measure: DAG run notes are free-text fields that could
    inadvertently contain sensitive runtime data (e.g. stack traces, file paths, user
    inputs). By allow-listing only the known sentinel value we prevent leaking any
    unintended information to the frontend.

    The endpoint polls Airflow internally (up to ``_NOTE_MAX_ATTEMPTS`` times with
    ``_NOTE_POLL_INTERVAL_S`` seconds between each attempt) to absorb the latency
    between the DAG run reaching FAILED state and the failure callback writing the
    note. The frontend therefore makes a single request and waits for the result.
    """
    # Note: this endpoint is intentionally not using auth checking as integrity link
    # table may have been removed in case of DAG run timeout, but we still want to be
    # able to check the note to display a proper message in the UI.

    try:
        executor = get_task_executor()
        note: str | None = None
        for _ in range(_NOTE_MAX_ATTEMPTS):
            note = executor.get_task_note(dag_id, dag_run_id)
            if note is not None:
                break
            await asyncio.sleep(_NOTE_POLL_INTERVAL_S)
        if note != "timed_out":
            return None
        return note
    except NotFoundException:
        raise HTTPException(status_code=404, detail=f"DAG run not found: {dag_id}/{dag_run_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Airflow error: {e}")


@router.get("/dags/{dag_id}/runs/{dag_run_id}/logs", response_class=PlainTextResponse)
def get_dag_run_logs(
    dag_id: str,
    dag_run_id: str,
    session: DatafeederSessionDep,
    geo_ctx: GeorchestraContextDep,
    org_id: OrgIdDep,
) -> str:
    intlink_id = dag_run_id.split("_")[0]  # Extract intlink_id from run_id pattern
    # Ensure the user has access to the integrity link associated with this DAG run
    load_authorized_integrity_link(intlink_id, AccessLevel.METADATA_READ, geo_ctx, session, org_id)
    executor = get_task_executor()
    return executor.get_task_logs(dag_id, dag_run_id)
