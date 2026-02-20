"""Job service — create, list, get, cancel jobs and dispatch to workers."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.job import Job
from backend.models.upload import Upload
from backend.schemas.job import JobCreate


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(self, payload: JobCreate, user_id: uuid.UUID) -> Job:
        """Create a new job record and link uploads."""
        job = Job(
            user_id=user_id,
            source_type=payload.source_type,
            title=payload.title,
            text_content=payload.text_content,
            settings=payload.settings.model_dump(),
            status="pending",
            current_step="Queued",
        )
        self.db.add(job)
        await self.db.flush()

        # Link uploads to this job
        upload_ids: list[uuid.UUID] = []
        if payload.pdf_upload_id:
            upload_ids.append(payload.pdf_upload_id)
        upload_ids.extend(payload.image_upload_ids)
        if payload.music_upload_id:
            upload_ids.append(payload.music_upload_id)

        if upload_ids:
            result = await self.db.execute(
                select(Upload).where(Upload.id.in_(upload_ids), Upload.user_id == user_id)
            )
            for upload in result.scalars():
                upload.job_id = job.id

        await self.db.flush()
        return job

    async def get_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> Job | None:
        result = await self.db.execute(
            select(Job).where(Job.id == job_id, Job.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Job], int]:
        """Return (jobs, total_count) for a user with optional status filter."""
        query = select(Job).where(Job.user_id == user_id)
        count_query = select(func.count()).select_from(Job).where(Job.user_id == user_id)

        if status:
            query = query.where(Job.status == status)
            count_query = count_query.where(Job.status == status)

        query = query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        jobs = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return jobs, total

    async def update_progress(
        self, job_id: uuid.UUID, status: str, step: str, progress: float
    ) -> None:
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.status = status
            job.current_step = step
            job.progress = progress
            if status == "completed":
                job.completed_at = datetime.now(timezone.utc)
            elif status in ("classifying", "scripting", "voiceover", "backgrounds", "composing", "exporting") and not job.started_at:
                job.started_at = datetime.now(timezone.utc)

    async def fail_job(self, job_id: uuid.UUID, error: str) -> None:
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.status = "failed"
            job.error_message = error
            job.completed_at = datetime.now(timezone.utc)

    async def cancel_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        job = await self.get_job(job_id, user_id)
        if not job:
            return False
        if job.status in ("completed", "failed", "cancelled"):
            return False
        job.status = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        return True

    async def delete_job(self, job_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        job = await self.get_job(job_id, user_id)
        if not job:
            return False
        await self.db.delete(job)
        return True

    async def set_video_id(self, job_id: uuid.UUID, video_id: uuid.UUID) -> None:
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            job.video_id = video_id
