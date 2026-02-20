"""Video service — create records, serve files, generate thumbnails."""

import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.video import Video
from backend.utils.storage import LocalStorage


class VideoService:
    def __init__(self, db: AsyncSession, storage: LocalStorage):
        self.db = db
        self.storage = storage

    async def create_video(
        self,
        user_id: uuid.UUID,
        title: str,
        local_path: Path,
        duration_seconds: float = 0.0,
        resolution: str = "1920x1080",
        metadata: dict | None = None,
    ) -> Video:
        """Store a generated video file and create a DB record."""
        file_size = local_path.stat().st_size if local_path.exists() else 0
        key = self.storage.generate_key(user_id, "videos", f"{title}.mp4")
        await self.storage.store(local_path, key)

        video = Video(
            user_id=user_id,
            title=title,
            file_path=key,
            file_size=file_size,
            duration_seconds=duration_seconds,
            resolution=resolution,
            metadata_json=metadata or {},
        )
        self.db.add(video)
        await self.db.flush()
        return video

    async def get_video(self, video_id: uuid.UUID, user_id: uuid.UUID) -> Video | None:
        result = await self.db.execute(
            select(Video).where(Video.id == video_id, Video.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_videos(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Video], int]:
        query = (
            select(Video)
            .where(Video.user_id == user_id)
            .order_by(Video.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        count_query = select(func.count()).select_from(Video).where(Video.user_id == user_id)

        result = await self.db.execute(query)
        videos = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return videos, total

    async def get_file_path(self, video_id: uuid.UUID, user_id: uuid.UUID) -> Path | None:
        video = await self.get_video(video_id, user_id)
        if not video:
            return None
        try:
            return await self.storage.retrieve(video.file_path)
        except FileNotFoundError:
            return None

    async def delete_video(self, video_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        video = await self.get_video(video_id, user_id)
        if not video:
            return False
        try:
            await self.storage.delete(video.file_path)
        except FileNotFoundError:
            pass
        await self.db.delete(video)
        return True
