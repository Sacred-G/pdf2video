"""Upload API routes — PDF, images, music."""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.upload import UploadResponse
from backend.services.upload_service import UploadService
from backend.utils.storage import get_storage

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/pdf", response_model=list[UploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UploadService(db, get_storage())
    try:
        uploads = await service.save_multiple(files, "pdf", user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return uploads


@router.post("/images", response_model=list[UploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_images(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UploadService(db, get_storage())
    try:
        uploads = await service.save_multiple(files, "image", user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return uploads


@router.post("/music", response_model=list[UploadResponse], status_code=status.HTTP_201_CREATED)
async def upload_music(
    files: list[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UploadService(db, get_storage())
    try:
        uploads = await service.save_multiple(files, "music", user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return uploads
