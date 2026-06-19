"""Guardian API router."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError

from app.api.deps import get_bearer_token
from app.api.providers import provide_guardian
from app.config.security import decode_access_token

from .schemas import (
    GuardianInviteRequest,
    GuardianInviteResponse,
    GuardianAcceptRequest,
    GuardianRelationshipResponse,
    GuardianListResponse,
)
from .service import GuardianService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/guardian", tags=["guardian"])


@router.post("/invite", response_model=GuardianInviteResponse)
async def invite_guardian(
    request: GuardianInviteRequest,
    token: str = Depends(get_bearer_token),
    guardian_service: GuardianService = Depends(provide_guardian),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Invite a guardian.
    
    Blind user invites a family user to be their guardian.
    Guardian must already have an account.
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

    result = await guardian_service.invite_guardian(
        blind_user_id=user_id,
        guardian_email=request.guardian_email,
        permissions=request.permissions,
    )

    return {
        "success": True,
        "data": result,
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.post("/accept")
async def accept_invitation(
    request: GuardianAcceptRequest,
    token: str = Depends(get_bearer_token),
    guardian_service: GuardianService = Depends(provide_guardian),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Accept a guardian invitation.
    
    Guardian accepts an invitation from a blind user.
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

    result = await guardian_service.accept_invite(
        guardian_user_id=user_id,
        invite_id=request.invite_id,
    )

    return {
        "success": True,
        "data": result,
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.post("/reject")
async def reject_invitation(
    request: GuardianAcceptRequest,
    token: str = Depends(get_bearer_token),
    guardian_service: GuardianService = Depends(provide_guardian),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """Reject a guardian invitation."""
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

    result = await guardian_service.reject_invite(
        guardian_user_id=user_id,
        invite_id=request.invite_id,
    )

    return {
        "success": True,
        "data": result,
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.delete("/{relationship_id}")
async def remove_guardian(
    relationship_id: str,
    token: str = Depends(get_bearer_token),
    guardian_service: GuardianService = Depends(provide_guardian),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Remove a guardian relationship.
    
    Can be called by either blind user or guardian.
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

    result = await guardian_service.remove_guardian(
        user_id=user_id,
        relationship_id=relationship_id,
    )

    return {
        "success": True,
        "data": result,
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.get("/me")
async def get_my_guardians(
    token: str = Depends(get_bearer_token),
    guardian_service: GuardianService = Depends(provide_guardian),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Get my guardians (if I'm a blind user).
    
    Returns all guardian relationships for the authenticated blind user.
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

    relationships = await guardian_service.get_my_guardians(user_id)

    return {
        "success": True,
        "data": {"relationships": relationships},
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.get("/blind-users")
async def get_blind_users(
    token: str = Depends(get_bearer_token),
    guardian_service: GuardianService = Depends(provide_guardian),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Get blind users I'm monitoring (if I'm a guardian).
    
    Returns all blind users monitored by the authenticated guardian.
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

    blind_users = await guardian_service.get_my_blind_users(user_id)

    return {
        "success": True,
        "data": {"blind_users": blind_users},
        "trace_id": x_trace_id or "trace-local-demo",
    }
