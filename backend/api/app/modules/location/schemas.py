"""Location schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class LocationUpdateRequest(BaseModel):
    """Request to update current location."""
    lat: float = Field(description="Latitude")
    lng: float = Field(description="Longitude")
    accuracy: float | None = Field(default=None, description="Accuracy in meters")


class LocationResponse(BaseModel):
    """Response with location data."""
    user_id: str
    lat: float
    lng: float
    accuracy: float | None
    updated_at: str
