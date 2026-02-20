"""
FastAPI application factory — entry point for the PDF2Video backend.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.v1.router import v1_router
from backend.config import settings
from backend.db.base import Base
from backend.db.session import engine
from backend.middleware.error_handler import ErrorHandlerMiddleware, RequestIdMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    # Create all tables (dev convenience — use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure storage directories exist
    for subdir in ("uploads/pdf", "uploads/image", "uploads/music", "videos", "temp"):
        (settings.STORAGE_LOCAL_PATH / subdir).mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown: dispose engine
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="PDF2Video API",
        description="Backend API for the PDF2Video cinematic generation pipeline.",
        version="2.0.0",
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost first) ──────
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── API Routes ───────────────────────────────────────
    app.include_router(v1_router)

    # ── Static file serving for stored media ─────────────
    media_path = settings.STORAGE_LOCAL_PATH
    if media_path.exists():
        app.mount("/media", StaticFiles(directory=str(media_path)), name="media")

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
    )
