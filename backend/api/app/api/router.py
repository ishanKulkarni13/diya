from __future__ import annotations

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.safety.router import router as safety_router
from app.modules.assist.router import router as assist_router
from app.modules.guardian.router import router as guardian_router
from app.modules.location.router import router as location_router
from app.modules.notifications.router import router as notifications_router
from app.api.health import router as health_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router, prefix="")
api_router.include_router(auth_router)
api_router.include_router(safety_router)
api_router.include_router(assist_router)
api_router.include_router(guardian_router)
api_router.include_router(location_router)
api_router.include_router(notifications_router)
