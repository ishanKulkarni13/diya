"""
Gemini provider for the Assist module.

Wraps the google-genai SDK to provide structured image analysis.
This module is the only place in the codebase that imports google.genai.
"""

from __future__ import annotations

import logging
import time
from typing import Protocol

from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from ..exceptions import (
    ProviderError,
    AuthenticationError,
    QuotaExceededError,
    RateLimitError,
    TemporaryUnavailableError,
    TimeoutError,
    SafetyBlockedError,
    MalformedResponseError,
    UnknownProviderError,
)

logger = logging.getLogger(__name__)


# ── Structured output schema ────────────────────────────────────────────────

class GeminiAnalysisResult(BaseModel):
    """Schema used to constrain Gemini's JSON output."""

    spoken_text: str = Field(description="Concise spoken description for a visually impaired user (1-3 sentences)")
    display_text: str = Field(description="Short summary suitable for display on screen")
    hazards: list[str] = Field(default_factory=list, description="Immediate hazards or dangers detected")
    detected_objects: list[str] = Field(default_factory=list, description="Notable objects in the scene")
    confidence: float = Field(default=0.0, description="Confidence score from 0.0 to 1.0")


# ── Provider protocol ───────────────────────────────────────────────────────

class ImageAnalysisProvider(Protocol):
    """Protocol for any image analysis provider."""

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        intent_type: str,
    ) -> ProviderResult: ...


# ── Provider result ──────────────────────────────────────────────────────────

class ProviderResult:
    """Encapsulates the result of a provider call including metadata."""

    def __init__(
        self,
        analysis: GeminiAnalysisResult,
        provider_name: str,
        model_name: str,
        latency_ms: int,
    ) -> None:
        self.analysis = analysis
        self.provider_name = provider_name
        self.model_name = model_name
        self.latency_ms = latency_ms


# ── Gemini provider ─────────────────────────────────────────────────────────

class GeminiProvider:
    """Concrete provider that calls the Gemini API for multimodal analysis."""

    def __init__(self, api_key: str, model_name: str) -> None:
        self._model_name = model_name
        self._client = genai.Client(
            api_key=api_key,
            http_options={"timeout": 10.0}
        )

    @retry(
        retry=retry_if_exception_type((RateLimitError, TemporaryUnavailableError, TimeoutError)),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _execute_with_retry(self, prompt, image_part):
        try:
            return self._client.models.generate_content(
                model=self._model_name,
                contents=[prompt, image_part],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiAnalysisResult,
                ),
            )
        except APIError as e:
            code = getattr(e, "code", 500)
            if code == 401:
                raise AuthenticationError(f"Gemini authentication failed: {e}") from e
            elif code == 429:
                if "quota" in str(e).lower():
                    raise QuotaExceededError(f"Gemini quota exceeded: {e}") from e
                raise RateLimitError(f"Gemini rate limit exceeded: {e}") from e
            elif code in (500, 502, 503, 504):
                raise TemporaryUnavailableError(f"Gemini temporarily unavailable: {e}") from e
            else:
                raise UnknownProviderError(f"Gemini API error {code}: {e}") from e
        except Exception as e:
            error_name = type(e).__name__
            if "Timeout" in error_name:
                raise TimeoutError(f"Gemini request timed out: {e}") from e
            if "Connection" in error_name or "Network" in error_name:
                raise TemporaryUnavailableError(f"Gemini network error: {e}") from e
            raise UnknownProviderError(f"Unknown Gemini failure: {e}") from e

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        intent_type: str,
    ) -> ProviderResult:
        """
        Send an image to Gemini for structured analysis.

        The prompt is tailored for visually impaired navigation assistance.
        """
        prompt = self._build_prompt(intent_type)

        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)

        start_time = time.monotonic()

        response = self._execute_with_retry(prompt, image_part)

        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        logger.info(
            "Gemini analysis completed",
            extra={"model": self._model_name, "latency_ms": elapsed_ms},
        )

        if not response.parsed:
            logger.error("Gemini returned unparseable response")
            raise MalformedResponseError("Gemini returned an empty or unparseable response")

        return ProviderResult(
            analysis=response.parsed,
            provider_name="gemini",
            model_name=self._model_name,
            latency_ms=elapsed_ms,
        )

    @staticmethod
    def _build_prompt(intent_type: str) -> str:
        """
        Build the system prompt for Gemini.

        Prioritizes hazard detection and navigation for visually impaired users.
        """
        base_prompt = (
            "You are an assistive AI for a visually impaired user. "
            "Analyze this image and provide a response that prioritizes:\n"
            "1. Immediate hazards (obstacles, stairs, vehicles, wet floors)\n"
            "2. Navigation information (doorways, paths, intersections)\n"
            "3. Important objects the user should know about\n"
            "4. Any visible text (signs, labels, screens)\n"
            "5. Brief general scene description\n\n"
            "Keep the spoken_text to 1-3 concise sentences. "
            "Focus on what matters for safe mobility and awareness. "
            "Do not describe colors or aesthetics unless safety-relevant."
        )

        if intent_type == "describe_scene":
            return base_prompt
        elif intent_type == "read_text":
            return (
                "You are an assistive AI for a visually impaired user. "
                "Focus on reading all visible text in this image. "
                "Report signs, labels, screens, documents, and any printed or displayed text. "
                "Keep the spoken_text to 1-3 concise sentences."
            )
        else:
            return base_prompt


# Note: GeminiProviderError is removed. We use the hierarchy in app.modules.assist.exceptions
