from fastapi import APIRouter
from app.api.v1.endpoints import jobs, download

router = APIRouter(prefix="/api/v1")
router.include_router(jobs.router)
router.include_router(download.router)