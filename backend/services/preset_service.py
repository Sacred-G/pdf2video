"""Preset service — save/load/manage user presets."""

import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.preset import Preset
from backend.schemas.preset import PresetCreate, PresetUpdate


class PresetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_preset(self, payload: PresetCreate, user_id: uuid.UUID) -> Preset:
        """Create a new preset. If marked as default, unset other defaults first."""
        if payload.is_default:
            await self._clear_defaults(user_id)

        preset = Preset(
            user_id=user_id,
            name=payload.name,
            description=payload.description,
            settings=payload.settings.model_dump(),
            is_default=payload.is_default,
        )
        self.db.add(preset)
        await self.db.flush()
        return preset

    async def list_presets(self, user_id: uuid.UUID) -> list[Preset]:
        result = await self.db.execute(
            select(Preset)
            .where(Preset.user_id == user_id)
            .order_by(Preset.is_default.desc(), Preset.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_preset(self, preset_id: uuid.UUID, user_id: uuid.UUID) -> Preset | None:
        result = await self.db.execute(
            select(Preset).where(Preset.id == preset_id, Preset.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_default_preset(self, user_id: uuid.UUID) -> Preset | None:
        result = await self.db.execute(
            select(Preset).where(Preset.user_id == user_id, Preset.is_default == True)
        )
        return result.scalar_one_or_none()

    async def update_preset(
        self, preset_id: uuid.UUID, user_id: uuid.UUID, payload: PresetUpdate
    ) -> Preset | None:
        preset = await self.get_preset(preset_id, user_id)
        if not preset:
            return None

        if payload.name is not None:
            preset.name = payload.name
        if payload.description is not None:
            preset.description = payload.description
        if payload.settings is not None:
            preset.settings = payload.settings.model_dump()
        if payload.is_default is not None:
            if payload.is_default:
                await self._clear_defaults(user_id)
            preset.is_default = payload.is_default

        await self.db.flush()
        return preset

    async def delete_preset(self, preset_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        preset = await self.get_preset(preset_id, user_id)
        if not preset:
            return False
        await self.db.delete(preset)
        return True

    async def _clear_defaults(self, user_id: uuid.UUID) -> None:
        """Unset is_default on all presets for this user."""
        await self.db.execute(
            update(Preset)
            .where(Preset.user_id == user_id, Preset.is_default == True)
            .values(is_default=False)
        )
