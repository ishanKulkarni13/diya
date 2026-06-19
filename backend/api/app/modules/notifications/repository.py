"""Notification repository."""
from __future__ import annotations

from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DeviceToken


class NotificationRepository(Protocol):
    """Repository protocol for notification operations."""

    async def register_token(
        self,
        user_id: UUID,
        token: str,
        platform: str,
    ) -> DeviceToken: ...

    async def delete_token(self, token: str) -> None: ...

    async def get_user_tokens(self, user_id: UUID) -> list[DeviceToken]: ...


class SqlAlchemyNotificationRepository:
    """SQLAlchemy implementation of NotificationRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register_token(
        self,
        user_id: UUID,
        token: str,
        platform: str,
    ) -> DeviceToken:
        """Register a device token for push notifications."""
        # Check if token already exists
        query = select(DeviceToken).where(DeviceToken.token == token)
        result = await self._session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            # Update user_id and platform if changed
            existing.user_id = user_id
            existing.platform = platform
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        else:
            # Create new
            device_token = DeviceToken(
                id=uuid4(),
                user_id=user_id,
                token=token,
                platform=platform,
            )
            self._session.add(device_token)
            await self._session.commit()
            await self._session.refresh(device_token)
            return device_token

    async def delete_token(self, token: str) -> None:
        """Delete a device token."""
        stmt = delete(DeviceToken).where(DeviceToken.token == token)
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_user_tokens(self, user_id: UUID) -> list[DeviceToken]:
        """Get all device tokens for a user."""
        query = select(DeviceToken).where(DeviceToken.user_id == user_id)
        result = await self._session.execute(query)
        return list(result.scalars().all())
