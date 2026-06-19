from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """
    User model for 2ndEye.

    Roles: BLIND, FAMILY, ADMIN
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)


class AuthSession(Base):
    """
    Tracks active user sessions and refresh tokens.

    Supports rotation and revocation.
    """

    __tablename__ = "auth_sessions"

    user_id: Mapped[UUID] = mapped_column(index=True)
    refresh_token: Mapped[str] = mapped_column(String(512), index=True)
    token_version: Mapped[int] = mapped_column(default=1)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
