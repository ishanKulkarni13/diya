"""Guardian request and response schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class GuardianInviteRequest(BaseModel):
    """Request to invite a guardian."""
    guardian_email: EmailStr
    permissions: list[str] = Field(
        default_factory=lambda: [
            "VIEW_LOCATION",
            "VIEW_SAFETY_EVENTS",
            "RECEIVE_SOS",
            "RECEIVE_PUSH",
        ]
    )


class GuardianInviteResponse(BaseModel):
    """Response after creating a guardian invite."""
    invite_id: str
    guardian_email: str
    expires_at: str
    status: str


class GuardianAcceptRequest(BaseModel):
    """Request to accept a guardian invitation."""
    invite_id: str


class GuardianRelationshipResponse(BaseModel):
    """Response with guardian relationship details."""
    id: str
    blind_user_email: str
    guardian_email: str
    status: str
    permissions: list[str]
    accepted_at: str | None
    created_at: str


class GuardianListResponse(BaseModel):
    """Response listing all guardians for a blind user or all blind users for a guardian."""
    relationships: list[GuardianRelationshipResponse]


class GuardianBlindUserInfo(BaseModel):
    """Information about a blind user for guardian view."""
    id: str
    email: str
    last_location_update: str | None = None
    last_safety_event: str | None = None
