"""Location repository."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CurrentLocation


class LocationRepository(Protocol):
    """Repository protocol for location operations."""

    async def upsert_location(
        self,
        user_id: UUID,
        lat: float,
        lng: float,
        accuracy: float | None = None,
    ) -> CurrentLocation: ...

    async def get_location(self, user_id: UUID) -> CurrentLocation | None: ...


class SqlAlchemyLocationRepository:
    """SQLAlchemy implementation of LocationRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_location(
        self,
        user_id: UUID,
        lat: float,
        lng: float,
        accuracy: float | None = None,
    ) -> CurrentLocation:
        """Insert or update current location for a user."""
        # Try to get existing location
        existing = await self.get_location(user_id)

        if existing:
            # Update existing
            existing.lat = lat
            existing.lng = lng
            existing.accuracy = accuracy
            existing.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await self._session.commit()
            await self._session.refresh(existing)
            return existing
        else:
            # Create new
            location = CurrentLocation(
                id=uuid4(),
                user_id=user_id,
                lat=lat,
                lng=lng,
                accuracy=accuracy,
            )
            self._session.add(location)
            await self._session.commit()
            await self._session.refresh(location)
            return location

    async def get_location(self, user_id: UUID) -> CurrentLocation | None:
        """Get current location for a user."""
        query = select(CurrentLocation).where(CurrentLocation.user_id == user_id)
        result = await self._session.execute(query)
        return result.scalar_one_or_none()
