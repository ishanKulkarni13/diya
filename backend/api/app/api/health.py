from typing import Any, Dict
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.config.settings import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

@router.get("/health")
def health() -> dict[str, str]:
    """Legacy health endpoint."""
    return {"status": "ok", "service": settings.app.app_name}

@router.get("/live")
def live() -> dict[str, str]:
    """Liveness probe. Returns 200 if the app is running."""
    return {"status": "alive"}

@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness probe.
    Verifies DB connectivity and external provider configurations.
    """
    response: Dict[str, Any] = {"status": "ready"}
    
    # 1. Check Database
    try:
        await db.execute(text("SELECT 1"))
        response["database"] = "ok"
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        response["status"] = "not_ready"
        response["database"] = "unreachable"
    
    # 2. Check Gemini Provider
    if not settings.providers.gemini_api_key:
        response["gemini"] = "degraded"
    else:
        response["gemini"] = "ok"
    
    # Gemini degradation does not fail readiness, but DB failure does.
    if response["status"] == "not_ready":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )
        
    return response
