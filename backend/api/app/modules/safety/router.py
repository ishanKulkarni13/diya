from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_bearer_token
from app.config.security import decode_access_token
from app.db.session import get_db
from app.schemas import SafetyEventCreateRequest

from app.api.providers import provide_safety
from .repository import SqlAlchemySafetyEventRepository
from .service import SafetyEventService

router = APIRouter(prefix="/safety", tags=["safety"])


@router.post("/events")
async def create_safety_event(
    request: SafetyEventCreateRequest,
    token: str = Depends(get_bearer_token),
    idempotency_key: str | None = Header(default=None),
    safety_service: SafetyEventService = Depends(provide_safety),
) -> dict:
    """
    Create a safety event (e.g., SOS).

    Requires:
    - Authorization header with valid access token
    - Idempotency-Key header or idempotency_key in body

    Returns:
    - {success: true, data: {id, trace_id, timestamp}, trace_id}
    """
    # Use idempotency key from body if not in header
    effective_idempotency_key = idempotency_key or request.idempotency_key

    # Decode token to get user_id
    try:
        payload_decoded = decode_access_token(token)
    except JWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH.TOKEN.INVALID", "message": str(error)},
        ) from error

    user_id = payload_decoded.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH.TOKEN.INVALID", "message": "User ID not found in token"},
        )

    # Create safety event
    trace_id = str(uuid4())
    event = await safety_service.create_safety_event(
        user_id=user_id,
        event_type=request.type,
        payload=request.payload,
        trace_id=trace_id,
        idempotency_key=effective_idempotency_key,
    )

    # Return success response with envelope
    return {
        "success": True,
        "data": {
            "id": str(event.id),
            "trace_id": event.trace_id,
            "timestamp": event.created_at.isoformat(),
        },
        "trace_id": event.trace_id,
    }
