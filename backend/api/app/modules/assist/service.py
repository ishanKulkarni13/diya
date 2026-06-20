"""
Assist service layer.

Orchestrates image analysis by delegating to the configured provider
and mapping provider results into the Assist response contract.

Following the same pattern as SafetyEventService and AuthService:
- Router handles HTTP parsing and dependency injection
- Service handles business logic and provider orchestration
- Provider handles external API communication
"""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status

from app.api.errors import (
    ASSIST_PROVIDER_UNAVAILABLE,
    ASSIST_TIMEOUT,
    ASSIST_QUOTA_EXCEEDED,
    ASSIST_RATE_LIMIT,
    ASSIST_PROVIDER_FAILED,
    ASSIST_MALFORMED_RESPONSE,
)

from .providers.gemini import GeminiProvider, ProviderResult
from .exceptions import (
    ProviderError,
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    TemporaryUnavailableError,
    TimeoutError,
    MalformedResponseError,
)
from .schemas import (
    AssistResponse,
    AssistResponseData,
    AssistTurnData,
    ProviderInfo,
)

logger = logging.getLogger(__name__)


class AssistService:
    """Service layer for Assist operations."""

    def __init__(self, provider: GeminiProvider) -> None:
        self._provider = provider

    async def analyze_image(
        self,
        session_id: str,
        image_bytes: bytes,
        mime_type: str,
        intent_data: dict,
        trigger_data: dict,
        idempotency_key: str | None = None,
    ) -> AssistResponse:
        """
        Analyze an image using the configured AI provider.

        Accepts raw image bytes and parsed request data.
        Returns a fully constructed AssistResponse.

        Raises HTTPException on provider failures to maintain
        consistent error handling with the rest of the backend.
        """
        intent_type = intent_data.get("type", "describe_scene")
        turn_id = str(uuid.uuid4())
        trace_id = str(uuid.uuid4())

        logger.info(
            "Starting assist analysis",
            extra={
                "session_id": session_id,
                "turn_id": turn_id,
                "intent_type": intent_type,
                "image_size_bytes": len(image_bytes),
                "mime_type": mime_type,
            },
        )

        try:
            result: ProviderResult = await self._provider.analyze_image(
                image_bytes=image_bytes,
                mime_type=mime_type,
                intent_type=intent_type,
            )
        except ProviderError as e:
            logger.error(
                f"Provider analysis failed: {type(e).__name__}: {str(e)}",
                extra={"session_id": session_id, "turn_id": turn_id, "error": str(e), "error_type": type(e).__name__},
                exc_info=True,
            )
            
            if isinstance(e, RateLimitError):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"code": ASSIST_RATE_LIMIT, "message": "AI service is receiving too many requests", "retry_after": 10},
                ) from e
            elif isinstance(e, QuotaExceededError):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"code": ASSIST_QUOTA_EXCEEDED, "message": "AI service quota exceeded", "retry_after": 3600},
                ) from e
            elif isinstance(e, TimeoutError):
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail={"code": ASSIST_TIMEOUT, "message": "AI service timed out", "retry_after": 30},
                ) from e
            elif isinstance(e, TemporaryUnavailableError):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": ASSIST_PROVIDER_UNAVAILABLE, "message": "AI service temporarily unavailable", "retry_after": 30},
                ) from e
            elif isinstance(e, MalformedResponseError):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": ASSIST_MALFORMED_RESPONSE, "message": "AI service returned invalid response"},
                ) from e
            elif isinstance(e, AuthenticationError):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"code": ASSIST_PROVIDER_FAILED, "message": "AI service misconfigured"},
                ) from e
            else:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail={"code": ASSIST_PROVIDER_FAILED, "message": "Image analysis failed. Please try again."},
                ) from e

        logger.info(
            "Assist analysis completed",
            extra={
                "session_id": session_id,
                "turn_id": turn_id,
                "latency_ms": result.latency_ms,
                "provider": result.provider_name,
                "model": result.model_name,
            },
        )

        return self._build_response(
            turn_id=turn_id,
            session_id=session_id,
            trace_id=trace_id,
            result=result,
        )

    @staticmethod
    def _build_response(
        turn_id: str,
        session_id: str,
        trace_id: str,
        result: ProviderResult,
    ) -> AssistResponse:
        """Map a ProviderResult into the Assist API response contract."""
        analysis = result.analysis

        response_data = AssistResponseData(
            spoken_text=analysis.spoken_text,
            display_text=analysis.display_text,
            confidence=analysis.confidence,
            follow_up_mode="available",
            hazards=analysis.hazards,
            detected_objects=analysis.detected_objects,
        )

        provider_info = ProviderInfo(
            name=result.provider_name,
            model=result.model_name,
            latency_ms=result.latency_ms,
        )

        turn_data = AssistTurnData(
            turn_id=turn_id,
            session_id=session_id,
            status="completed",
            response=response_data,
            provider=provider_info,
        )

        return AssistResponse(data=turn_data, trace_id=trace_id)
