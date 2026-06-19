"""Notification schemas."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of notifications."""
    INVITE = "INVITE"
    SOS = "SOS"
    LOW_BATTERY = "LOW_BATTERY"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"


class DeviceTokenRequest(BaseModel):
    """Request to register a device token."""
    token: str
    platform: str = Field(description="Platform: ios, android, web")


class NotificationPreferencesResponse(BaseModel):
    """User's notification preferences."""
    push_enabled: bool = True
    sms_enabled: bool = False
    email_enabled: bool = False
