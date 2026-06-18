from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_bearer_token
from app.db.session import get_db
from app.schemas import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest

from app.api.providers import provide_auth
from .repository import SqlAlchemyAuthRepository
from .service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(provide_auth),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    token_pair = await auth_service.login(request)
    return {
        "success": True,
        "data": {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "expires_in": token_pair.expires_in,
            "session_id": token_pair.session_id,
            "token_version": token_pair.token_version,
            "user": {
                "id": token_pair.user.id,
                "email": token_pair.user.email,
                "roles": token_pair.user.roles,
            },
        },
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.post("/register")
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(provide_auth),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    token_pair = await auth_service.register(request)
    return {
        "success": True,
        "data": {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "expires_in": token_pair.expires_in,
            "session_id": token_pair.session_id,
            "token_version": token_pair.token_version,
            "user": {
                "id": token_pair.user.id,
                "email": token_pair.user.email,
                "roles": token_pair.user.roles,
            },
        },
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.post("/refresh")
async def refresh(
    request: RefreshRequest,
    auth_service: AuthService = Depends(provide_auth),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    token_pair = await auth_service.refresh(request)
    return {
        "success": True,
        "data": {
            "access_token": token_pair.access_token,
            "refresh_token": token_pair.refresh_token,
            "expires_in": token_pair.expires_in,
            "session_id": token_pair.session_id,
            "token_version": token_pair.token_version,
            "user": {
                "id": token_pair.user.id,
                "email": token_pair.user.email,
                "roles": token_pair.user.roles,
            },
        },
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.post("/logout")
async def logout(
    request: LogoutRequest | None = None,
    token: str = Depends(get_bearer_token),
    auth_service: AuthService = Depends(provide_auth),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    await auth_service.logout(request, token)
    return {
        "success": True,
        "data": {"status": "logged_out"},
        "trace_id": x_trace_id or "trace-local-demo",
    }


@router.get("/me")
async def me(
    token: str = Depends(get_bearer_token),
    auth_service: AuthService = Depends(provide_auth),
    x_trace_id: str | None = Header(default=None),
) -> dict:
    me_response = await auth_service.me(token)
    return {
        "success": True,
        "data": {
            "user": {
                "id": me_response.user.id,
                "email": me_response.user.email,
                "roles": me_response.user.roles,
            },
            "session_id": me_response.session_id,
            "token_version": me_response.token_version,
        },
        "trace_id": x_trace_id or "trace-local-demo",
    }
