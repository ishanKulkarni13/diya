"""Safety service layer."""
from __future__ import annotations

import logging
from uuid import UUID

from app.modules.auth.repository import AuthRepository
from app.modules.guardian.repository import GuardianRepository
from app.modules.guardian.models import GuardianPermission, GuardianStatus
from app.modules.notifications.service import NotificationService
from app.modules.notifications.repository import NotificationRepository

from .models import SafetyEvent
from .repository import SafetyEventRepository

logger = logging.getLogger(__name__)


class SafetyEventService:
    """Service layer for safety operations."""

    def __init__(
        self,
        repository: SafetyEventRepository,
        auth_repo: AuthRepository | None = None,
        guardian_repo: GuardianRepository | None = None,
        notification_service: NotificationService | None = None,
        notification_repo: NotificationRepository | None = None,
    ) -> None:
        self._repository = repository
        self._auth_repo = auth_repo
        self._guardian_repo = guardian_repo
        self._notification_service = notification_service
        self._notification_repo = notification_repo

    async def create_safety_event(
        self,
        user_id: str,
        event_type: str,
        payload: dict,
        trace_id: str,
        idempotency_key: str | None = None,
    ) -> SafetyEvent:
        """
        Create a safety event.

        If idempotency_key is provided and a matching event already exists,
        return the existing event (idempotent behavior).
        
        If event_type is SOS and guardians are configured, notify all active guardians.
        """
        event = await self._repository.create_event(
            user_id=UUID(user_id),
            event_type=event_type,
            payload=payload,
            trace_id=trace_id,
            idempotency_key=idempotency_key,
        )

        # If this is an SOS event and we have guardian/notification services, notify guardians
        if (
            event_type == "SOS"
            and self._auth_repo
            and self._guardian_repo
            and self._notification_service
            and self._notification_repo
        ):
            await self._notify_guardians_of_sos(user_id, str(event.id))

        return event

    async def _notify_guardians_of_sos(self, blind_user_id: str, event_id: str) -> None:
        """
        Notify all active guardians of an SOS event.
        
        Args:
            blind_user_id: UUID of blind user who triggered SOS
            event_id: Safety event ID
        """
        try:
            blind_uuid = UUID(blind_user_id)

            # Get blind user info
            blind_user = await self._auth_repo.get_user_by_id(blind_uuid)
            if not blind_user:
                logger.warning(f"Blind user {blind_user_id} not found for SOS notification")
                return

            # Get all active guardians
            relationships = await self._guardian_repo.get_guardians_for_user(blind_uuid)
            active_guardians = [
                r
                for r in relationships
                if r.status == GuardianStatus.ACTIVE.value
                and GuardianPermission.RECEIVE_SOS.value in r.permissions
            ]

            if not active_guardians:
                logger.info(f"No active guardians to notify for SOS from {blind_user_id}")
                return

            logger.info(
                f"Notifying {len(active_guardians)} guardians of SOS",
                extra={
                    "blind_user_id": blind_user_id,
                    "event_id": event_id,
                    "guardian_count": len(active_guardians),
                },
            )

            # Send notification to each guardian
            for relationship in active_guardians:
                guardian = await self._auth_repo.get_user_by_id(relationship.guardian_user_id)
                if not guardian:
                    continue

                # Get guardian's device tokens
                tokens = await self._notification_repo.get_user_tokens(guardian.id)
                device_token = tokens[0].token if tokens else None

                # Send SOS notification
                await self._notification_service.send_sos_notification(
                    recipient_token=device_token,
                    recipient_email=guardian.email,
                    recipient_phone=guardian.phone_number,
                    blind_user_email=blind_user.email,
                    event_id=event_id,
                )

                logger.info(
                    f"SOS notification sent to guardian {guardian.email}",
                    extra={
                        "guardian_id": str(guardian.id),
                        "blind_user_id": blind_user_id,
                        "event_id": event_id,
                    },
                )

        except Exception as e:
            # Don't fail the SOS creation if notification fails
            logger.error(
                f"Failed to notify guardians of SOS: {e}",
                exc_info=True,
                extra={
                    "blind_user_id": blind_user_id,
                    "event_id": event_id,
                },
            )

    async def get_events_by_user(self, user_id: str, limit: int = 100) -> list[SafetyEvent]:
        """Retrieve all safety events for a user."""
        return await self._repository.get_events_by_user(UUID(user_id), limit)
