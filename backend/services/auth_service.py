"""Authentication service — register, login, token management."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User
from backend.utils.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, email: str, password: str, display_name: str = "") -> tuple[User, str, str]:
        """Create a new user and return (user, access_token, refresh_token)."""
        existing = await self.db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")

        user = User(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name or email.split("@")[0],
        )
        self.db.add(user)
        await self.db.flush()

        access = create_access_token(user.id, user.email)
        refresh = create_refresh_token(user.id)
        return user, access, refresh

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        """Authenticate and return (user, access_token, refresh_token)."""
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is disabled")

        access = create_access_token(user.id, user.email)
        refresh = create_refresh_token(user.id)
        return user, access, refresh

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def refresh_tokens(self, user_id: uuid.UUID) -> tuple[str, str] | None:
        """Issue new token pair for an existing user."""
        user = await self.get_user_by_id(user_id)
        if not user or not user.is_active:
            return None
        access = create_access_token(user.id, user.email)
        refresh = create_refresh_token(user.id)
        return access, refresh
