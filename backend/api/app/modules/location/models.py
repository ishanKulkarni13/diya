"""Location models."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CurrentLocation(Base):
    """
    Stores the current location for each user.
    
    Only one row per user - updated on each location update.
    No history tracking in V1.
    """

    __tablename__ = "current_locations"

    user_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_current_location_user"),
    )
