"""Job request/response schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel


class JobSettings(BaseModel):
    voice: str = "onyx"
    resolution: str = "1920x1080"
    fps: int = 30
    generate_backgrounds: bool = True


class JobCreate(BaseModel):
    source_type: str  # "pdf" | "text_images"
    title: str = "Untitled"
    pdf_upload_id: uuid.UUID | None = None
    image_upload_ids: list[uuid.UUID] = []
    music_upload_id: uuid.UUID | None = None
    text_content: str | None = None
    settings: JobSettings = JobSettings()


class JobProgress(BaseModel):
    status: str
    step: str
    progress: float


class JobResponse(BaseModel):
    id: uuid.UUID
    title: str
    source_type: str
    status: str
    progress: float
    current_step: str
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    video_id: uuid.UUID | None = None
    settings: dict = {}

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    page_size: int
