from __future__ import annotations

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.safety.router import router as safety_router
from app.modules.assist.router import router as assist_router
from app.api.health import router as health_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, prefix="")
api_router.include_router(auth_router)
api_router.include_router(safety_router)
api_router.include_router(assist_router)
