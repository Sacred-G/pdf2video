"""Preset request/response schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel


class PresetSettings(BaseModel):
    voice: str = "onyx"
    resolution: str = "1920x1080"
    fps: int = 30
    generate_backgrounds: bool = True


class PresetCreate(BaseModel):
    name: str
    description: str = ""
    settings: PresetSettings = PresetSettings()
    is_default: bool = False


class PresetUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    settings: PresetSettings | None = None
    is_default: bool | None = None


class PresetResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    settings: dict
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PresetListResponse(BaseModel):
    items: list[PresetResponse]
    total: int
