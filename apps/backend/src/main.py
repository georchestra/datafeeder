import importlib.metadata
import os
from datetime import datetime, timezone
from uuid import UUID

from data_manipulation import hello
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from geonetwork import GnApi

from src.api.deps import SessionDep
from src.api.main import api_router
from src.core.config import get_settings
from src.models.integrity_link import IntegrityLink


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


@app.post("/print_dag_success", tags=["Callbacks"])
def dag_success_callback(
    session: SessionDep,
    integrity_link_id: str = Query(..., description="IntegrityLink ID"),
    staging_table_name: str = Query(..., max_length=63, description="Staging table name"),
):
    """
    Success callback endpoint called by Airflow DAG on successful completion.
    Updates the existing IntegrityLink record with job duration.

    Args:
        session: Database session (injected)
        integrity_link_id: IntegrityLink UUID (required)
        staging_table_name: Staging table name (required, max 63 chars, for verification)

    Returns:
        Success message with updated IntegrityLink details
    """
    # Query existing IntegrityLink
    integrity_link = session.get(IntegrityLink, UUID(integrity_link_id))
    if not integrity_link:
        raise HTTPException(status_code=404, detail="IntegrityLink not found")

    # Verify staging table name matches
    if integrity_link.staging_table_name != staging_table_name:
        raise HTTPException(
            status_code=400,
            detail=f"Staging table name mismatch: expected {integrity_link.staging_table_name}, got {staging_table_name}",
        )

    # Calculate job duration
    now = datetime.now(timezone.utc)
    # Ensure created_at is timezone-aware (assume UTC if naive)
    created_at = (
        integrity_link.created_at.replace(tzinfo=timezone.utc)
        if integrity_link.created_at.tzinfo is None
        else integrity_link.created_at
    )
    retrieve_time = now - created_at

    # Update IntegrityLink
    integrity_link.retrieve_time = retrieve_time
    integrity_link.last_staging_retrieved_at = now
    session.commit()
    session.refresh(integrity_link)

    return {
        "message": "DAG success callback processed",
        "integrity_link_id": str(integrity_link.id),
        "owner": integrity_link.integrity_owner,
        "organization": integrity_link.integrity_organization,
        "staging_table_name": integrity_link.staging_table_name,
        "retrieve_time_seconds": retrieve_time.total_seconds(),
    }


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
