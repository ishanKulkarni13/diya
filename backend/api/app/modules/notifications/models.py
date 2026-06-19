"""Notification models."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeviceToken(Base):
    """
    Stores device tokens for push notifications.
    
    One user can have multiple tokens (multiple devices).
    """

    __tablename__ = "device_tokens"

    user_id: Mapped[UUID] = mapped_column(index=True)
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(20))  # ios, android, web

    __table_args__ = (
        UniqueConstraint("user_id", "token", name="uq_device_token"),
    )
