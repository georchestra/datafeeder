from fastapi import APIRouter

from src.api.routes import airflow, utils
from src.api.routes.ingestion import process, staging

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(airflow.router)
api_router.include_router(process.router)
api_router.include_router(staging.router)
