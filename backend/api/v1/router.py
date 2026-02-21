"""Aggregates all v1 API routers into a single router."""

from fastapi import APIRouter

from backend.api.v1.auth import router as auth_router
from backend.api.v1.health import router as health_router
from backend.api.v1.jobs import router as jobs_router
from backend.api.v1.jobs_progress import router as jobs_progress_router
from backend.api.v1.presets import router as presets_router
from backend.api.v1.uploads import router as uploads_router
from backend.api.v1.videos import router as videos_router

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(auth_router)
v1_router.include_router(health_router)
v1_router.include_router(jobs_router)
v1_router.include_router(jobs_progress_router)
v1_router.include_router(presets_router)
v1_router.include_router(uploads_router)
v1_router.include_router(videos_router)
