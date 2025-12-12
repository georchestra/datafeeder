import importlib.metadata
import os

from data_manipulation import hello
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from geonetwork import GnApi

from src.api.main import api_router
from src.core.config import get_settings


def _get_debug_flag() -> bool:
    """Get DEBUG flag from environment variable."""
    value = os.getenv("DEBUG")
    if value is None:
        return False
    value_lower = value.lower()
    if value_lower == "true":
        return True
    return False


DEBUG = _get_debug_flag()

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


@app.get("/print_dag_success", tags=["Health"])
def read_print_dag_success():
    print("DAG success callback works!")
    return {"message": "DAG success callback works!"}


@app.get("/print_dag_failure", tags=["Health"])
def read_print_dag_failure():
    print("DAG failure callback works!")
    return {"message": "DAG failure callback works!"}


@app.get("/geonetwork", tags=["Health"])
def read_geonetwork():
    gnapi: GnApi = GnApi(
        api_url=f"{get_settings().georchestra_config.get('geonetwork.target', 'gateway_routes')}srv/api",
        credentials=None,
        verifytls=False,
    )
    return {"Hello": gnapi._get_version().json()}  # type: ignore[reportPrivateUsage]


if DEBUG:

    @app.get("/config", tags=["Health"], response_class=HTMLResponse)
    def read_config():
        return get_settings().georchestra_config.tostr() + get_settings().tostr()
