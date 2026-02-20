"""
Backend-specific configuration using Pydantic BaseSettings.
Loads from .env and provides typed access to all backend settings.
"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://pdf2video:password@localhost:5432/pdf2video"

    # ── Redis ────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Authentication ───────────────────────────────────
    JWT_SECRET_KEY: str = "change-me-to-a-random-256-bit-string"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Storage ──────────────────────────────────────────
    STORAGE_BACKEND: str = "local"
    STORAGE_LOCAL_PATH: Path = Path("./storage")

    # ── Server ───────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    MAX_UPLOAD_SIZE_MB: int = 100
    MAX_CONCURRENT_JOBS: int = 3

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
