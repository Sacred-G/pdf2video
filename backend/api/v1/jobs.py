"""Job API routes — create, list, get, cancel, retry, delete."""

import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.job import JobCreate, JobListResponse, JobResponse
from backend.services.job_service import JobService
from backend.services.upload_service import UploadService
from backend.services.video_service import VideoService
from backend.utils.progress import progress_manager
from backend.utils.storage import get_storage
from backend.workers.video_worker import run_video_job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    payload: JobCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job_service = JobService(db)
    job = await job_service.create_job(payload, user.id)
    await db.commit()

    # Resolve upload paths for the worker
    storage = get_storage()
    upload_service = UploadService(db, storage)

    pdf_path = None
    if payload.pdf_upload_id:
        pdf_path = await upload_service.get_upload_path(payload.pdf_upload_id, user.id)

    image_paths = []
    image_labels = []
    for img_id in payload.image_upload_ids:
        upload = await upload_service.get_upload(img_id, user.id)
        if upload:
            try:
                p = await storage.retrieve(upload.stored_path)
                image_paths.append(p)
                image_labels.append(upload.original_filename)
            except FileNotFoundError:
                pass

    music_path = None
    if payload.music_upload_id:
        music_path = await upload_service.get_upload_path(payload.music_upload_id, user.id)

    # Dispatch to background worker
    async def _run_and_finalize():
        async with (await _get_fresh_session()) as session:
            js = JobService(session)
            vs = VideoService(session, storage)
            try:
                result_path = await run_video_job(
                    job_id=job.id,
                    user_id=user.id,
                    source_type=payload.source_type,
                    title=payload.title,
                    job_settings=payload.settings.model_dump(),
                    pdf_path=pdf_path,
                    image_paths=image_paths,
                    image_labels=image_labels,
                    music_path=music_path,
                    text_content=payload.text_content,
                )
                # Create video record
                video = await vs.create_video(
                    user_id=user.id,
                    title=payload.title,
                    local_path=result_path,
                    resolution=payload.settings.resolution,
                )
                await js.set_video_id(job.id, video.id)
                await js.update_progress(job.id, "completed", "Complete!", 1.0)
                await session.commit()
            except Exception as e:
                await js.fail_job(job.id, str(e))
                await session.commit()
            finally:
                progress_manager.remove(job.id)

    asyncio.create_task(_run_and_finalize())

    return job


async def _get_fresh_session():
    """Create a fresh async session for background tasks."""
    from backend.db.session import async_session_factory
    return async_session_factory()


@router.get("", response_model=JobListResponse)
async def list_jobs(
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)
    jobs, total = await service.list_jobs(user.id, page, page_size, status_filter)
    return JobListResponse(
        items=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)
    job = await service.get_job(job_id, user.id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)
    success = await service.cancel_job(job_id, user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found or cannot be cancelled")
    progress_manager.update(job_id, "cancelled", "Cancelled", 0.0)
    return {"message": "Job cancelled"}


@router.delete("/{job_id}")
async def delete_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = JobService(db)
    success = await service.delete_job(job_id, user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {"message": "Job deleted"}
