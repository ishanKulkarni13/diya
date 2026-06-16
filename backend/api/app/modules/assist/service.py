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

from .providers.gemini import GeminiProvider, GeminiProviderError, ProviderResult
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
            },
        )

        try:
            result: ProviderResult = await self._provider.analyze_image(
                image_bytes=image_bytes,
                mime_type=mime_type,
                intent_type=intent_type,
            )
        except GeminiProviderError as e:
            logger.error(
                "Provider analysis failed",
                extra={"session_id": session_id, "turn_id": turn_id, "error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "ASSIST.PROVIDER.FAILED",
                    "message": "Image analysis failed. Please try again.",
                },
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
