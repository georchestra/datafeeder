import importlib.metadata

from airflow_client.client.exceptions import ApiException
from airflow_client.client.models.dag_run_state import DagRunState
from data_manipulation import hello
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.main import api_router

from .services.airflow_client import get_dag_run_api

BACKEND_VERSION = importlib.metadata.version("datakern-backend")

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://localhost:4201"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.get("/", tags=["Health"])
def read_root():
    return {"Hello": hello()}


@app.get("/version", tags=["Health"])
def read_version():
    return {"version": BACKEND_VERSION}


@app.get("/airflow/dags/{dag_id}/runs/{dag_run_id}", tags=["Airflow"])
def get_dag_run_status(dag_id: str, dag_run_id: str) -> DagRunState:
    try:
        dag_run = get_dag_run_api().get_dag_run(dag_id, dag_run_id)
        return dag_run.state
    except ApiException as e:
        raise e
