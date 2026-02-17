from fastapi import APIRouter

from src.api import internal
from src.api.routes import airflow, data_groups, geonetwork, metadata_groups, settings, utils
from src.api.routes.ingestion import integrity_link, integrity_links, process, staging

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(airflow.router)
api_router.include_router(geonetwork.router)
api_router.include_router(settings.router)
api_router.include_router(process.router)
api_router.include_router(staging.router)
api_router.include_router(integrity_links.router)
api_router.include_router(integrity_link.router)
api_router.include_router(metadata_groups.router)
api_router.include_router(data_groups.router)
api_router.include_router(internal.router)
