"""Location service layer."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status

from app.modules.auth.repository import AuthRepository
from app.modules.guardian.repository import GuardianRepository
from app.modules.guardian.models import GuardianPermission, GuardianStatus

from .repository import LocationRepository

logger = logging.getLogger(__name__)


class LocationService:
    """Service layer for location operations."""

    def __init__(
        self,
        location_repo: LocationRepository,
        auth_repo: AuthRepository,
        guardian_repo: GuardianRepository,
    ) -> None:
        self._location_repo = location_repo
        self._auth_repo = auth_repo
        self._guardian_repo = guardian_repo

    async def update_location(
        self,
        user_id: str,
        lat: float,
        lng: float,
        accuracy: float | None = None,
    ) -> dict:
        """
        Update current location for a user.
        
        Args:
            user_id: UUID of user
            lat: Latitude
            lng: Longitude
            accuracy: Accuracy in meters (optional)
            
        Returns:
            Dictionary with location data
        """
        user_uuid = UUID(user_id)

        # Verify user exists
        user = await self._auth_repo.get_user_by_id(user_uuid)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "LOCATION.USER.NOT_FOUND", "message": "User not found"},
            )

        location = await self._location_repo.upsert_location(
            user_id=user_uuid,
            lat=lat,
            lng=lng,
            accuracy=accuracy,
        )

        logger.info(
            "Location updated",
            extra={
                "user_id": user_id,
                "lat": lat,
                "lng": lng,
                "accuracy": accuracy,
            },
        )

        return {
            "user_id": str(location.user_id),
            "lat": location.lat,
            "lng": location.lng,
            "accuracy": location.accuracy,
            "updated_at": location.updated_at.isoformat(),
        }

    async def get_my_location(self, user_id: str) -> dict:
        """Get current location for a user (their own)."""
        user_uuid = UUID(user_id)

        location = await self._location_repo.get_location(user_uuid)
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "LOCATION.NOT_FOUND",
                    "message": "No location data available",
                },
            )

        return {
            "user_id": str(location.user_id),
            "lat": location.lat,
            "lng": location.lng,
            "accuracy": location.accuracy,
            "updated_at": location.updated_at.isoformat(),
        }

    async def get_guardian_location(
        self,
        guardian_user_id: str,
        blind_user_id: str,
    ) -> dict:
        """
        Get location of a blind user as seen by their guardian.
        
        Validates guardian relationship and permissions.
        
        Args:
            guardian_user_id: UUID of guardian requesting location
            blind_user_id: UUID of blind user whose location is requested
            
        Returns:
            Dictionary with location data
            
        Raises:
            HTTPException: If no relationship or insufficient permissions
        """
        guardian_uuid = UUID(guardian_user_id)
        blind_uuid = UUID(blind_user_id)

        # Check guardian relationship
        relationship = await self._guardian_repo.get_active_relationship(
            blind_uuid, guardian_uuid
        )
        if not relationship or relationship.status != GuardianStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "LOCATION.NO_GUARDIAN_RELATIONSHIP",
                    "message": "You do not have an active guardian relationship with this user",
                },
            )

        # Check permissions
        if GuardianPermission.VIEW_LOCATION.value not in relationship.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "LOCATION.PERMISSION_DENIED",
                    "message": "You do not have permission to view this user's location",
                },
            )

        # Get location
        location = await self._location_repo.get_location(blind_uuid)
        if not location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "LOCATION.NOT_FOUND",
                    "message": "No location data available for this user",
                },
            )

        logger.info(
            "Guardian accessed location",
            extra={
                "guardian_id": guardian_user_id,
                "blind_user_id": blind_user_id,
            },
        )

        return {
            "user_id": str(location.user_id),
            "lat": location.lat,
            "lng": location.lng,
            "accuracy": location.accuracy,
            "updated_at": location.updated_at.isoformat(),
        }
