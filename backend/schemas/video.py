"""Video response schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel


class VideoResponse(BaseModel):
    id: uuid.UUID
    title: str
    file_size: int
    duration_seconds: float
    resolution: str
    thumbnail_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int
