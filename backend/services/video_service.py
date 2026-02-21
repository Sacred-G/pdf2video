"""Video service — create records, serve files, generate thumbnails."""

import logging
import subprocess
import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.video import Video
from backend.utils.storage import LocalStorage

logger = logging.getLogger(__name__)


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

        # Probe duration from the video file
        if duration_seconds == 0.0 and local_path.exists():
            duration_seconds = self._probe_duration(local_path)

        key = self.storage.generate_key(user_id, "videos", f"{title}.mp4")
        await self.storage.store(local_path, key)

        # Generate thumbnail
        thumb_key = key.rsplit(".", 1)[0] + "_thumb.jpg"
        thumb_path = await self._generate_thumbnail(local_path, thumb_key)

        video = Video(
            user_id=user_id,
            title=title,
            file_path=key,
            file_size=file_size,
            duration_seconds=duration_seconds,
            resolution=resolution,
            thumbnail_path=thumb_path,
            metadata_json=metadata or {},
        )
        self.db.add(video)
        await self.db.flush()
        return video

    def _probe_duration(self, video_path: Path) -> float:
        """Use ffprobe to get video duration in seconds."""
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet", "-show_entries",
                    "format=duration", "-of", "csv=p=0", str(video_path),
                ],
                capture_output=True, text=True, timeout=10,
            )
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning("Failed to probe duration for %s: %s", video_path, e)
            return 0.0

    async def _generate_thumbnail(self, video_path: Path, thumb_key: str) -> str | None:
        """Extract a frame at 2 seconds and store as thumbnail."""
        try:
            thumb_local = video_path.parent / f"{video_path.stem}_thumb.jpg"
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", str(video_path),
                    "-ss", "2", "-vframes", "1",
                    "-vf", "scale=640:-1",
                    "-q:v", "3", str(thumb_local),
                ],
                capture_output=True, timeout=15,
            )
            if thumb_local.exists():
                await self.storage.store(thumb_local, thumb_key)
                thumb_local.unlink(missing_ok=True)
                return thumb_key
        except Exception as e:
            logger.warning("Failed to generate thumbnail: %s", e)
        return None

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
