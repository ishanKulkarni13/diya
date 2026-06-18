"""
Centralized dependency providers for the API.
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


async def provide_auth(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Provide the AuthService with the current DB session."""
    repository = SqlAlchemyAuthRepository(db)
    return AuthService(repository)


async def provide_safety(db: AsyncSession = Depends(get_db)) -> SafetyEventService:
    """Provide the SafetyEventService with the current DB session."""
    repository = SqlAlchemySafetyEventRepository(db)
    return SafetyEventService(repository)


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


def provide_assist(gemini: GeminiProvider = Depends(provide_gemini)) -> AssistService:
    """Provide the AssistService with its dependencies."""
    return AssistService(gemini)
