from fastapi import APIRouter
from src.api.routes import internal_files

router = APIRouter(prefix="/internal")

router.include_router(internal_files.router)