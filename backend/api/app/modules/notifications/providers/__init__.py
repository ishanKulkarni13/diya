"""Notification providers."""
from __future__ import annotations

from typing import Protocol


class NotificationProvider(Protocol):
    """Protocol for notification providers."""

    async def send(
        self,
        recipient: str,
        title: str,
        body: str,
        data: dict | None = None,
    ) -> bool:
        """
        Send a notification.
        
        Args:
            recipient: Email, phone number, or device token depending on provider
            title: Notification title
            body: Notification body
            data: Optional additional data payload
            
        Returns:
            True if sent successfully, False otherwise
        """
        ...
