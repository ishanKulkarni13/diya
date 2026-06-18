from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.error_handlers import register_error_handlers
from app.api.router import api_router
from app.config.logging import setup_logging
from app.config.settings import settings
from app.db.session import async_session_factory
from app.api.middleware import RequestLoggingMiddleware
from app.modules.auth.repository import SqlAlchemyAuthRepository
from app.modules.auth.service import AuthService
from app.api.providers import provide_auth

setup_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle app startup and shutdown events.
    
    Includes demo data seeding using a one-off session.
    """
    logger.info("Starting up 2ndEye API...")
    
    # Seed demo users if they don't exist
    async with async_session_factory() as db:
        # Re-use the provider creation logic manually since Depends() is only for endpoints
        repository = SqlAlchemyAuthRepository(db)
        service = AuthService(repository)
        await service.seed_demo_users()
        logger.info("Demo users seeded (if missing)")

    yield
    
    logger.info("Shutting down 2ndEye API...")


app = FastAPI(title=settings.app.app_name, lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)

register_error_handlers(app)
app.include_router(api_router)


@app.get("/")
def root() -> dict[str, str]:
    logger.info("Root endpoint called")
    return {"message": settings.app.app_name}
