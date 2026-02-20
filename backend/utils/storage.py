"""File storage abstraction — local filesystem implementation."""

import shutil
import uuid
from pathlib import Path

from backend.config import settings


class LocalStorage:
    """Stores files on local filesystem under STORAGE_LOCAL_PATH."""

    def __init__(self):
        self.base = settings.STORAGE_LOCAL_PATH
        self.base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        return self.base / key

    async def store(self, local_path: Path, key: str) -> str:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(local_path), str(dest))
        return key

    async def store_bytes(self, data: bytes, key: str) -> str:
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return key

    async def retrieve(self, key: str) -> Path:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"Storage key not found: {key}")
        return path

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    async def get_url(self, key: str) -> str:
        return f"/media/{key}"

    def generate_key(self, user_id: uuid.UUID, folder: str, filename: str) -> str:
        ext = Path(filename).suffix
        unique = uuid.uuid4().hex[:12]
        return f"{folder}/{user_id}/{unique}{ext}"


def get_storage() -> LocalStorage:
    return LocalStorage()
