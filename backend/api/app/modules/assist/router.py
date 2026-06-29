"""
Assist router — thin HTTP layer.

Parses the multipart form data and delegates to AssistService.
Follows the same pattern as auth/router.py and safety/router.py.
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from jose import JWTError

from app.api.deps import get_bearer_token
from app.api.providers import provide_assist
from app.config.settings import settings
from app.config.security import decode_access_token

from .schemas import AssistResponse
from .service import AssistService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assist", tags=["assist"])


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/sessions/{session_id}/turns", response_model=AssistResponse)
async def create_assist_turn(
    session_id: str,
    intent_json: str = Form(...),
    trigger_json: str = Form(...),
    client_context_json: str = Form(...),
    image_file: UploadFile = File(...),
    token: str = Depends(get_bearer_token),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    assist_service: AssistService = Depends(provide_assist),
) -> AssistResponse:
    """
    Create an Assist turn.

    Accepts a multipart request with image and context JSON,
    analyzes the image using the configured AI provider,
    and returns a structured response.
    
    Requires authentication.
    """
    # Validate token
    try:
        payload = decode_access_token(token)
    except JWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH.TOKEN.INVALID", "message": str(error)},
        ) from error

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH.TOKEN.INVALID", "message": "User ID not found in token"},
        )

    logger.info(f"Received assist turn for session: {session_id}", extra={"user_id": user_id})

    # Parse JSON form fields
    try:
        intent_data = json.loads(intent_json)
        trigger_data = json.loads(trigger_json)
        client_context = json.loads(client_context_json)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse multipart JSON: {e}")
        return JSONResponse(
            status_code=400,
            content={"message": "Invalid JSON in form data"},
        )

    logger.info(
        "Parsed assist request",
        extra={
            "session_id": session_id,
            "intent": intent_data.get("type"),
            "image_filename": image_file.filename,
            "image_content_type": image_file.content_type,
        },
    )

    # Read image bytes (ephemeral — not persisted)
    image_bytes = await image_file.read()
    mime_type = image_file.content_type or "image/jpeg"
    
    # Log image upload diagnostics
    logger.info(
        f"[ROUTER] Image upload: filename={image_file.filename}, "
        f"content_type={image_file.content_type}, size={len(image_bytes)} bytes"
    )
    
    if len(image_bytes) >= 2:
        is_jpeg = image_bytes.startswith(b'\xff\xd8')
        logger.info(f"[ROUTER] Image magic bytes: {image_bytes[:2].hex()} (JPEG: {is_jpeg})")
    else:
        logger.error(f"[ROUTER] Image too small: {len(image_bytes)} bytes")
    
    if len(image_bytes) == 0:
        logger.error("[ROUTER] Empty image received from client")
        return JSONResponse(
            status_code=400,
            content={
                "code": "ASSIST.IMAGE.EMPTY",
                "message": "Empty image data received. Please ensure image is captured correctly."
            },
        )

    # Delegate to service
    return await assist_service.analyze_image(
        session_id=session_id,
        image_bytes=image_bytes,
        mime_type=mime_type,
        intent_data=intent_data,
        trigger_data=trigger_data,
        idempotency_key=idempotency_key,
    )
