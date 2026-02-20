"""Upload request/response schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel


class UploadResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_size: int
    mime_type: str
    stored_path: str
    file_type: str
    created_at: datetime

    model_config = {"from_attributes": True}
