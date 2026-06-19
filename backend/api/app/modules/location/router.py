"""Location API router."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, status
from jose import JWTError

from app.api.deps import get_bearer_token
from app.config.security import decode_access_token

from .schemas import LocationUpdateRequest, LocationResponse
from .service import LocationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/location", tags=["location"])


@router.post("/update", response_model=LocationResponse)
async def update_location(
    request: LocationUpdateRequest,
    token: str = Depends(get_bearer_token),
    location_service: LocationService = Depends(),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Update current location.
    
    Blind user updates their current location.
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

    result = await location_service.update_location(
        user_id=user_id,
        lat=request.lat,
        lng=request.lng,
        accuracy=request.accuracy,
    )

    return {
        "success": True,
        "data": result,
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.get("/me", response_model=LocationResponse)
async def get_my_location(
    token: str = Depends(get_bearer_token),
    location_service: LocationService = Depends(),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """Get my current location."""
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

    result = await location_service.get_my_location(user_id)

    return {
        "success": True,
        "data": result,
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.get("/guardian/{blind_user_id}", response_model=LocationResponse)
async def get_guardian_location(
    blind_user_id: str,
    token: str = Depends(get_bearer_token),
    location_service: LocationService = Depends(),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    """
    Get location of a blind user (guardian view).
    
    Guardian retrieves location of a blind user they monitor.
    Validates guardian relationship and permissions.
    """
    try:
        payload = decode_access_token(token)
    except JWTError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH.TOKEN.INVALID", "message": str(error)},
        ) from error

    guardian_user_id = payload.get("sub")
    if not guardian_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "AUTH.TOKEN.INVALID", "message": "User ID not found in token"},
        )

    result = await location_service.get_guardian_location(
        guardian_user_id=guardian_user_id,
        blind_user_id=blind_user_id,
    )

    return {
        "success": True,
        "data": result,
        "trace_id": x_trace_id or "trace-local-demo",
    }
