from fastapi import APIRouter

from src.api.routes import airflow, utils

api_router = APIRouter()
api_router.include_router(utils.router)
api_router.include_router(airflow.router)
