"""Notification service - orchestrates notification delivery across providers."""
from __future__ import annotations

import logging
from uuid import UUID

from .providers import NotificationProvider
from .providers.fcm import FCMProvider
from .providers.mock_sms import MockSMSProvider
from .providers.mock_email import MockEmailProvider
from .schemas import NotificationType

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service layer for notifications.
    
    Orchestrates notification delivery across multiple providers.
    Guardian module knows only this service - not individual providers.
    """

    def __init__(
        self,
        fcm_provider: FCMProvider,
        sms_provider: MockSMSProvider,
        email_provider: MockEmailProvider,
    ) -> None:
        self._fcm = fcm_provider
        self._sms = sms_provider
        self._email = email_provider

    async def send_guardian_invite(
        self,
        recipient_email: str,
        recipient_phone: str | None,
        blind_user_email: str,
        invite_id: str,
    ) -> None:
        """
        Send guardian invitation notifications.
        
        Args:
            recipient_email: Guardian's email
            recipient_phone: Guardian's phone (optional)
            blind_user_email: Email of the blind user sending invite
            invite_id: Invitation ID for acceptance
        """
        title = "Guardian Invitation"
        body = f"{blind_user_email} has invited you to be their guardian on 2ndEye"
        
        logger.info(
            "Sending guardian invite notification",
            extra={
                "recipient_email": recipient_email,
                "blind_user": blind_user_email,
                "invite_id": invite_id,
            },
        )

        # Always send email (mock)
        await self._email.send(recipient_email, title, body, {"invite_id": invite_id})

        # Send SMS if phone number is available (mock)
        if recipient_phone:
            await self._sms.send(
                recipient_phone,
                title,
                f"{body}. Invite ID: {invite_id}",
                {"invite_id": invite_id},
            )

    async def send_sos_notification(
        self,
        recipient_token: str | None,
        recipient_email: str,
        recipient_phone: str | None,
        blind_user_email: str,
        event_id: str,
    ) -> None:
        """
        Send SOS notification to a guardian.
        
        Args:
            recipient_token: FCM device token (optional)
            recipient_email: Guardian's email
            recipient_phone: Guardian's phone (optional)
            blind_user_email: Email of blind user who triggered SOS
            event_id: Safety event ID
        """
        title = "🚨 SOS Alert"
        body = f"{blind_user_email} has triggered an SOS alert"

        logger.info(
            "Sending SOS notification",
            extra={
                "recipient_email": recipient_email,
                "blind_user": blind_user_email,
                "event_id": event_id,
                "has_token": recipient_token is not None,
            },
        )

        # Try push notification first (real FCM if configured)
        if recipient_token:
            sent = await self._fcm.send(
                recipient_token,
                title,
                body,
                {"event_id": event_id, "type": "SOS"},
            )
            if sent:
                logger.info(f"SOS push notification sent to {recipient_email}")
                return

        # Fallback to email (mock)
        await self._email.send(recipient_email, title, body, {"event_id": event_id})

        # Also send SMS if available (mock)
        if recipient_phone:
            await self._sms.send(
                recipient_phone,
                title,
                f"{body}. Event ID: {event_id}",
                {"event_id": event_id},
            )

    async def send_low_battery_notification(
        self,
        recipient_token: str | None,
        recipient_email: str,
        blind_user_email: str,
        battery_level: int,
    ) -> None:
        """Send low battery notification to guardian."""
        title = "Low Battery Alert"
        body = f"{blind_user_email}'s device battery is at {battery_level}%"

        logger.info(
            "Sending low battery notification",
            extra={
                "recipient_email": recipient_email,
                "blind_user": blind_user_email,
                "battery_level": battery_level,
            },
        )

        if recipient_token:
            await self._fcm.send(recipient_token, title, body, {"battery_level": battery_level})
        else:
            await self._email.send(recipient_email, title, body, {"battery_level": battery_level})
