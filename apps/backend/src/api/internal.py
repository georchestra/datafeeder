from fastapi import APIRouter

from src.api.routes import internal_files
from src.api.routes.ingestion import process, staging

router = APIRouter(prefix="/internal")

router.include_router(internal_files.router)
router.include_router(staging.internal_router)
router.include_router(process.internal_router)
