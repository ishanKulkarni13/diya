"""
Centralized dependency providers for the API.

Provider functions are organized in dependency order:
1. Low-level providers (no dependencies on other providers)
2. Mid-level services (depend on low-level providers)
3. High-level services (depend on mid-level services)
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.session import get_db

from app.modules.auth.repository import SqlAlchemyAuthRepository
from app.modules.auth.service import AuthService

from app.modules.safety.repository import SqlAlchemySafetyEventRepository
from app.modules.safety.service import SafetyEventService

from app.modules.assist.providers.gemini import GeminiProvider
from app.modules.assist.service import AssistService

from app.modules.guardian.repository import SqlAlchemyGuardianRepository
from app.modules.guardian.service import GuardianService

from app.modules.location.repository import SqlAlchemyLocationRepository
from app.modules.location.service import LocationService

from app.modules.notifications.repository import SqlAlchemyNotificationRepository
from app.modules.notifications.providers.fcm import FCMProvider
from app.modules.notifications.providers.mock_sms import MockSMSProvider
from app.modules.notifications.providers.mock_email import MockEmailProvider
from app.modules.notifications.service import NotificationService


# ──────────────────────────────────────────────────────────────────────────────
# Low-level providers (no dependencies on other providers)
# ──────────────────────────────────────────────────────────────────────────────


def provide_gemini() -> GeminiProvider:
    """Provide the configured GeminiProvider."""
    api_key = settings.providers.gemini_api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "ASSIST.PROVIDER.NOT_CONFIGURED",
                "message": "Gemini API key is not configured.",
            },
        )
    return GeminiProvider(
        api_key=api_key,
        model_name=settings.providers.gemini_model_name,
    )


def provide_notification_service() -> NotificationService:
    """Provide the NotificationService with configured providers."""
    fcm = FCMProvider(credentials_path=settings.providers.fcm_credentials_path)
    sms = MockSMSProvider()
    email = MockEmailProvider()
    return NotificationService(fcm_provider=fcm, sms_provider=sms, email_provider=email)


async def provide_notification_repo(
    db: AsyncSession = Depends(get_db)
) -> SqlAlchemyNotificationRepository:
    """Provide the NotificationRepository."""
    return SqlAlchemyNotificationRepository(db)


# ──────────────────────────────────────────────────────────────────────────────
# Mid-level services (depend on low-level providers only)
# ──────────────────────────────────────────────────────────────────────────────


async def provide_auth(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Provide the AuthService with the current DB session."""
    repository = SqlAlchemyAuthRepository(db)
    return AuthService(repository)


def provide_assist(gemini: GeminiProvider = Depends(provide_gemini)) -> AssistService:
    """Provide the AssistService with its dependencies."""
    return AssistService(gemini)


async def provide_location(db: AsyncSession = Depends(get_db)) -> LocationService:
    """Provide the LocationService with its dependencies."""
    location_repo = SqlAlchemyLocationRepository(db)
    auth_repo = SqlAlchemyAuthRepository(db)
    guardian_repo = SqlAlchemyGuardianRepository(db)
    return LocationService(location_repo, auth_repo, guardian_repo)


# ──────────────────────────────────────────────────────────────────────────────
# High-level services (depend on mid-level services)
# ──────────────────────────────────────────────────────────────────────────────


async def provide_guardian(
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(provide_notification_service),
) -> GuardianService:
    """Provide the GuardianService with its dependencies."""
    guardian_repo = SqlAlchemyGuardianRepository(db)
    auth_repo = SqlAlchemyAuthRepository(db)
    return GuardianService(guardian_repo, auth_repo, notification_service)


async def provide_safety(
    db: AsyncSession = Depends(get_db),
    notification_service: NotificationService = Depends(provide_notification_service),
) -> SafetyEventService:
    """Provide the SafetyEventService with the current DB session and notification service."""
    safety_repo = SqlAlchemySafetyEventRepository(db)
    auth_repo = SqlAlchemyAuthRepository(db)
    guardian_repo = SqlAlchemyGuardianRepository(db)
    notification_repo = SqlAlchemyNotificationRepository(db)
    
    return SafetyEventService(
        safety_repo,
        auth_repo=auth_repo,
        guardian_repo=guardian_repo,
        notification_service=notification_service,
        notification_repo=notification_repo,
    )
