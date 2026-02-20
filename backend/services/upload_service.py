"""Upload service — handle file uploads, validation, storage."""

import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models.upload import Upload
from backend.utils.storage import LocalStorage


ALLOWED_MIME = {
    "pdf": {"application/pdf"},
    "image": {"image/png", "image/jpeg", "image/webp", "image/bmp", "image/gif"},
    "music": {"audio/mpeg", "audio/wav", "audio/ogg", "audio/mp4", "audio/x-wav"},
}


class UploadService:
    def __init__(self, db: AsyncSession, storage: LocalStorage):
        self.db = db
        self.storage = storage

    async def save_upload(
        self,
        file: UploadFile,
        file_type: str,
        user_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
    ) -> Upload:
        """Validate and store an uploaded file, returning the Upload record."""
        if file_type not in ALLOWED_MIME:
            raise ValueError(f"Unknown file type: {file_type}")

        mime = file.content_type or ""
        if mime not in ALLOWED_MIME[file_type]:
            raise ValueError(f"Invalid MIME type '{mime}' for {file_type} upload")

        data = await file.read()
        size_mb = len(data) / (1024 * 1024)
        if size_mb > settings.MAX_UPLOAD_SIZE_MB:
            raise ValueError(f"File too large ({size_mb:.1f} MB). Max is {settings.MAX_UPLOAD_SIZE_MB} MB.")

        key = self.storage.generate_key(user_id, f"uploads/{file_type}", file.filename or "file")
        await self.storage.store_bytes(data, key)

        upload = Upload(
            user_id=user_id,
            job_id=job_id,
            file_type=file_type,
            original_filename=file.filename or "file",
            stored_path=key,
            file_size=len(data),
            mime_type=mime,
        )
        self.db.add(upload)
        await self.db.flush()
        return upload

    async def save_multiple(
        self,
        files: list[UploadFile],
        file_type: str,
        user_id: uuid.UUID,
    ) -> list[Upload]:
        """Save multiple files of the same type."""
        results = []
        for f in files:
            upload = await self.save_upload(f, file_type, user_id)
            results.append(upload)
        return results

    async def get_upload(self, upload_id: uuid.UUID, user_id: uuid.UUID) -> Upload | None:
        from sqlalchemy import select
        result = await self.db.execute(
            select(Upload).where(Upload.id == upload_id, Upload.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_upload_path(self, upload_id: uuid.UUID, user_id: uuid.UUID) -> Path | None:
        upload = await self.get_upload(upload_id, user_id)
        if not upload:
            return None
        return await self.storage.retrieve(upload.stored_path)
