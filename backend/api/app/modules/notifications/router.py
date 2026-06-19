"""Notification API router."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError

from app.api.deps import get_bearer_token
from app.api.providers import provide_notification_repo
from app.config.security import decode_access_token

from .schemas import DeviceTokenRequest, NotificationPreferencesResponse
from .repository import NotificationRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/register-token")
async def register_device_token(
    request: DeviceTokenRequest,
    token: str = Depends(get_bearer_token),
    notification_repo: NotificationRepository = Depends(provide_notification_repo),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Register a device token for push notifications.
    
    User registers their device to receive push notifications.
    """
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

    device_token = await notification_repo.register_token(
        user_id=UUID(user_id),
        token=request.token,
        platform=request.platform,
    )

    logger.info(
        "Device token registered",
        extra={
            "user_id": user_id,
            "platform": request.platform,
        },
    )

    return {
        "success": True,
        "data": {
            "token_id": str(device_token.id),
            "platform": device_token.platform,
        },
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.delete("/token")
async def delete_device_token(
    device_token: str,
    token: str = Depends(get_bearer_token),
    notification_repo: NotificationRepository = Depends(provide_notification_repo),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Delete a device token.
    
    User unregisters a device from receiving push notifications.
    """
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

    await notification_repo.delete_token(device_token)

    logger.info(
        "Device token deleted",
        extra={"user_id": user_id},
    )

    return {
        "success": True,
        "data": {"status": "deleted"},
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    token: str = Depends(get_bearer_token),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Get notification preferences.
    
    V1: Returns hardcoded preferences.
    Future: Store per-user preferences in database.
    """
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

    # V1: Hardcoded preferences
    # TODO: Store and retrieve from database
    preferences = {
        "push_enabled": True,
        "sms_enabled": False,  # Mock only
        "email_enabled": False,  # Mock only
    }

    return {
        "success": True,
        "data": preferences,
        "trace_id": x_trace_id or "trace-local-demo",
    }
