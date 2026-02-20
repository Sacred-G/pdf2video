"""Health check endpoints."""

import subprocess
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    return {"status": "ok"}


@router.get("/gpu")
async def gpu_check():
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True, text=True, timeout=5,
        )
        has_nvenc = "h264_nvenc" in result.stdout
    except Exception:
        has_nvenc = False

    return {"nvenc_available": has_nvenc, "encoder": "h264_nvenc" if has_nvenc else "libx264"}
