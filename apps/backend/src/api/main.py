from fastapi import APIRouter

from src.api.routes import airflow, callbacks, import_router, utils

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(airflow.router)
api_router.include_router(import_router.router)
api_router.include_router(callbacks.router)
