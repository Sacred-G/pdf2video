"""SSE endpoint for real-time job progress streaming."""

import uuid

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse

from backend.dependencies import get_current_user
from backend.models.user import User
from backend.utils.progress import progress_manager

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}/progress")
async def stream_job_progress(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
):
    """SSE stream of progress updates for a specific job."""
    return StreamingResponse(
        progress_manager.subscribe(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
