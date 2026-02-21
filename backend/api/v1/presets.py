"""Preset API routes — save/load video generation settings."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.preset import (
    PresetCreate,
    PresetListResponse,
    PresetResponse,
    PresetUpdate,
)
from backend.services.preset_service import PresetService

router = APIRouter(prefix="/presets", tags=["presets"])


@router.get("", response_model=PresetListResponse)
async def list_presets(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PresetService(db)
    presets = await service.list_presets(user.id)
    return PresetListResponse(
        items=[PresetResponse.model_validate(p) for p in presets],
        total=len(presets),
    )


@router.get("/default", response_model=PresetResponse | None)
async def get_default_preset(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PresetService(db)
    preset = await service.get_default_preset(user.id)
    if not preset:
        return None
    return preset


@router.get("/{preset_id}", response_model=PresetResponse)
async def get_preset(
    preset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PresetService(db)
    preset = await service.get_preset(preset_id, user.id)
    if not preset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
    return preset


@router.post("", response_model=PresetResponse, status_code=status.HTTP_201_CREATED)
async def create_preset(
    payload: PresetCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PresetService(db)
    preset = await service.create_preset(payload, user.id)
    await db.commit()
    return preset


@router.put("/{preset_id}", response_model=PresetResponse)
async def update_preset(
    preset_id: uuid.UUID,
    payload: PresetUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PresetService(db)
    preset = await service.update_preset(preset_id, user.id, payload)
    if not preset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
    await db.commit()
    return preset


@router.delete("/{preset_id}")
async def delete_preset(
    preset_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = PresetService(db)
    success = await service.delete_preset(preset_id, user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found")
    await db.commit()
    return {"message": "Preset deleted"}
