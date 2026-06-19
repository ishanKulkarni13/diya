"""Guardian repository for database operations."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import GuardianRelationship, GuardianInvite, GuardianStatus


class GuardianRepository(Protocol):
    """Repository protocol for guardian operations."""

    async def create_invite(
        self,
        blind_user_id: UUID,
        guardian_email: str,
        expires_at: datetime,
    ) -> GuardianInvite: ...

    async def get_invite_by_id(self, invite_id: UUID) -> GuardianInvite | None: ...

    async def get_pending_invite(
        self, blind_user_id: UUID, guardian_email: str
    ) -> GuardianInvite | None: ...

    async def create_relationship(
        self,
        blind_user_id: UUID,
        guardian_user_id: UUID,
        permissions: list[str],
    ) -> GuardianRelationship: ...

    async def get_relationship_by_id(
        self, relationship_id: UUID
    ) -> GuardianRelationship | None: ...

    async def get_active_relationship(
        self, blind_user_id: UUID, guardian_user_id: UUID
    ) -> GuardianRelationship | None: ...

    async def get_guardians_for_user(
        self, blind_user_id: UUID
    ) -> list[GuardianRelationship]: ...

    async def get_blind_users_for_guardian(
        self, guardian_user_id: UUID
    ) -> list[GuardianRelationship]: ...

    async def update_relationship_status(
        self, relationship_id: UUID, status: str
    ) -> GuardianRelationship: ...

    async def delete_relationship(self, relationship_id: UUID) -> None: ...


class SqlAlchemyGuardianRepository:
    """SQLAlchemy implementation of GuardianRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_invite(
        self,
        blind_user_id: UUID,
        guardian_email: str,
        expires_at: datetime,
    ) -> GuardianInvite:
        """Create a new guardian invitation."""
        invite = GuardianInvite(
            id=uuid4(),
            blind_user_id=blind_user_id,
            guardian_email=guardian_email,
            expires_at=expires_at,
        )
        self._session.add(invite)
        await self._session.commit()
        await self._session.refresh(invite)
        return invite

    async def get_invite_by_id(self, invite_id: UUID) -> GuardianInvite | None:
        """Get an invitation by ID."""
        return await self._session.get(GuardianInvite, invite_id)

    async def get_pending_invite(
        self, blind_user_id: UUID, guardian_email: str
    ) -> GuardianInvite | None:
        """Get a pending (not accepted/rejected) invitation."""
        query = select(GuardianInvite).where(
            and_(
                GuardianInvite.blind_user_id == blind_user_id,
                GuardianInvite.guardian_email == guardian_email,
                GuardianInvite.accepted_at.is_(None),
                GuardianInvite.rejected_at.is_(None),
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def create_relationship(
        self,
        blind_user_id: UUID,
        guardian_user_id: UUID,
        permissions: list[str],
    ) -> GuardianRelationship:
        """Create a new guardian relationship."""
        relationship = GuardianRelationship(
            id=uuid4(),
            blind_user_id=blind_user_id,
            guardian_user_id=guardian_user_id,
            status=GuardianStatus.ACTIVE.value,
            permissions=permissions,
            accepted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self._session.add(relationship)
        await self._session.commit()
        await self._session.refresh(relationship)
        return relationship

    async def get_relationship_by_id(
        self, relationship_id: UUID
    ) -> GuardianRelationship | None:
        """Get a relationship by ID."""
        return await self._session.get(GuardianRelationship, relationship_id)

    async def get_active_relationship(
        self, blind_user_id: UUID, guardian_user_id: UUID
    ) -> GuardianRelationship | None:
        """Get an active relationship between two users."""
        query = select(GuardianRelationship).where(
            and_(
                GuardianRelationship.blind_user_id == blind_user_id,
                GuardianRelationship.guardian_user_id == guardian_user_id,
                GuardianRelationship.status == GuardianStatus.ACTIVE.value,
            )
        )
        result = await self._session.execute(query)
        return result.scalar_one_or_none()

    async def get_guardians_for_user(
        self, blind_user_id: UUID
    ) -> list[GuardianRelationship]:
        """Get all guardians for a blind user."""
        query = select(GuardianRelationship).where(
            GuardianRelationship.blind_user_id == blind_user_id
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_blind_users_for_guardian(
        self, guardian_user_id: UUID
    ) -> list[GuardianRelationship]:
        """Get all blind users monitored by a guardian."""
        query = select(GuardianRelationship).where(
            and_(
                GuardianRelationship.guardian_user_id == guardian_user_id,
                GuardianRelationship.status == GuardianStatus.ACTIVE.value,
            )
        )
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def update_relationship_status(
        self, relationship_id: UUID, status: str
    ) -> GuardianRelationship:
        """Update the status of a relationship."""
        relationship = await self.get_relationship_by_id(relationship_id)
        if relationship is None:
            raise ValueError(f"Relationship {relationship_id} not found")
        
        relationship.status = status
        await self._session.commit()
        await self._session.refresh(relationship)
        return relationship

    async def delete_relationship(self, relationship_id: UUID) -> None:
        """Delete a guardian relationship."""
        relationship = await self.get_relationship_by_id(relationship_id)
        if relationship is not None:
            await self._session.delete(relationship)
            await self._session.commit()
