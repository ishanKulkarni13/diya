"""Guardian relationship models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GuardianStatus(str, Enum):
    """Status of a guardian relationship."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"
    REMOVED = "REMOVED"


class GuardianPermission(str, Enum):
    """Permissions a guardian can have."""
    VIEW_LOCATION = "VIEW_LOCATION"
    VIEW_BATTERY = "VIEW_BATTERY"
    VIEW_SAFETY_EVENTS = "VIEW_SAFETY_EVENTS"
    RECEIVE_SOS = "RECEIVE_SOS"
    RECEIVE_PUSH = "RECEIVE_PUSH"


class GuardianRelationship(Base):
    """
    Represents a guardian relationship between a blind user and a family user.
    
    One blind user can have multiple guardians.
    One guardian can monitor multiple blind users.
    """

    __tablename__ = "guardian_relationships"

    blind_user_id: Mapped[UUID] = mapped_column(index=True)
    guardian_user_id: Mapped[UUID] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(20), default=GuardianStatus.PENDING.value)
    permissions: Mapped[list[str]] = mapped_column(JSON, default=list)
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    __table_args__ = (
        UniqueConstraint("blind_user_id", "guardian_user_id", name="uq_guardian_relationship"),
    )


class GuardianInvite(Base):
    """
    Tracks guardian invitations before they are accepted.
    
    Once accepted, the invitation is linked to the GuardianRelationship.
    """

    __tablename__ = "guardian_invites"

    blind_user_id: Mapped[UUID] = mapped_column(index=True)
    guardian_email: Mapped[str] = mapped_column(String(255), index=True)
    relationship_id: Mapped[UUID | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime] = mapped_column()
    accepted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(nullable=True)
