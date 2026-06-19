"""Guardian service layer."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status

from app.config.settings import settings
from app.modules.auth.repository import AuthRepository
from app.modules.notifications.service import NotificationService

from .models import GuardianPermission, GuardianStatus
from .repository import GuardianRepository

logger = logging.getLogger(__name__)


class GuardianService:
    """Service layer for guardian operations."""

    def __init__(
        self,
        guardian_repo: GuardianRepository,
        auth_repo: AuthRepository,
        notification_service: NotificationService,
    ) -> None:
        self._guardian_repo = guardian_repo
        self._auth_repo = auth_repo
        self._notification_service = notification_service

    async def invite_guardian(
        self,
        blind_user_id: str,
        guardian_email: str,
        permissions: list[str],
    ) -> dict:
        """
        Create a guardian invitation.
        
        Validates that:
        - Guardian user exists
        - Guardian has 'family' role
        - No active relationship already exists
        - No pending invite already exists
        
        Args:
            blind_user_id: UUID of blind user sending invite
            guardian_email: Email of guardian to invite
            permissions: List of permission strings
            
        Returns:
            Dictionary with invite details
            
        Raises:
            HTTPException: If validation fails
        """
        blind_uuid = UUID(blind_user_id)

        # Validate that blind user exists
        blind_user = await self._auth_repo.get_user_by_id(blind_uuid)
        if not blind_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "GUARDIAN.USER.NOT_FOUND", "message": "Blind user not found"},
            )

        # Validate that guardian user exists
        guardian_user = await self._auth_repo.get_user_by_email(guardian_email)
        if not guardian_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "GUARDIAN.GUARDIAN.NOT_FOUND",
                    "message": f"Guardian user with email {guardian_email} does not exist. They must create an account first.",
                },
            )

        # Validate guardian has family role
        if "family" not in guardian_user.roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "GUARDIAN.INVALID_ROLE",
                    "message": "Guardian must have 'family' role",
                },
            )

        # Check for existing active relationship
        existing = await self._guardian_repo.get_active_relationship(
            blind_uuid, guardian_user.id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "GUARDIAN.RELATIONSHIP.EXISTS",
                    "message": "Active guardian relationship already exists",
                },
            )

        # Check for pending invite
        pending = await self._guardian_repo.get_pending_invite(blind_uuid, guardian_email)
        if pending:
            # Check if expired
            if pending.expires_at > datetime.now(timezone.utc).replace(tzinfo=None):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "GUARDIAN.INVITE.PENDING",
                        "message": "A pending invitation already exists",
                    },
                )

        # Create invitation
        expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
            days=settings.guardian.invite_expiry_days
        )
        invite = await self._guardian_repo.create_invite(
            blind_user_id=blind_uuid,
            guardian_email=guardian_email,
            expires_at=expires_at,
        )

        logger.info(
            f"Guardian invite created: {invite.id}",
            extra={
                "invite_id": str(invite.id),
                "blind_user_id": str(blind_uuid),
                "guardian_email": guardian_email,
            },
        )

        # Send notification
        await self._notification_service.send_guardian_invite(
            recipient_email=guardian_email,
            recipient_phone=guardian_user.phone_number,
            blind_user_email=blind_user.email,
            invite_id=str(invite.id),
        )

        return {
            "invite_id": str(invite.id),
            "guardian_email": guardian_email,
            "expires_at": invite.expires_at.isoformat(),
            "status": "PENDING",
        }

    async def accept_invite(
        self,
        guardian_user_id: str,
        invite_id: str,
    ) -> dict:
        """
        Accept a guardian invitation.
        
        Args:
            guardian_user_id: UUID of guardian accepting invite
            invite_id: UUID of invitation
            
        Returns:
            Dictionary with relationship details
            
        Raises:
            HTTPException: If validation fails
        """
        guardian_uuid = UUID(guardian_user_id)
        invite_uuid = UUID(invite_id)

        # Get invite
        invite = await self._guardian_repo.get_invite_by_id(invite_uuid)
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "GUARDIAN.INVITE.NOT_FOUND", "message": "Invitation not found"},
            )

        # Validate guardian is the intended recipient
        guardian_user = await self._auth_repo.get_user_by_id(guardian_uuid)
        if not guardian_user or guardian_user.email != invite.guardian_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "GUARDIAN.INVITE.FORBIDDEN",
                    "message": "This invitation is not for you",
                },
            )

        # Check if already accepted
        if invite.accepted_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "GUARDIAN.INVITE.ALREADY_ACCEPTED",
                    "message": "Invitation already accepted",
                },
            )

        # Check if rejected
        if invite.rejected_at:
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "code": "GUARDIAN.INVITE.REJECTED",
                    "message": "Invitation was rejected",
                },
            )

        # Check if expired
        if invite.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail={
                    "code": "GUARDIAN.INVITE.EXPIRED",
                    "message": "Invitation has expired",
                },
            )

        # Create relationship with default permissions
        default_permissions = [
            GuardianPermission.VIEW_LOCATION.value,
            GuardianPermission.VIEW_SAFETY_EVENTS.value,
            GuardianPermission.RECEIVE_SOS.value,
            GuardianPermission.RECEIVE_PUSH.value,
        ]

        relationship = await self._guardian_repo.create_relationship(
            blind_user_id=invite.blind_user_id,
            guardian_user_id=guardian_uuid,
            permissions=default_permissions,
        )

        # Mark invite as accepted
        invite.accepted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        invite.relationship_id = relationship.id

        logger.info(
            f"Guardian relationship created: {relationship.id}",
            extra={
                "relationship_id": str(relationship.id),
                "blind_user_id": str(invite.blind_user_id),
                "guardian_user_id": str(guardian_uuid),
            },
        )

        return {
            "relationship_id": str(relationship.id),
            "status": "ACTIVE",
            "permissions": relationship.permissions,
        }

    async def reject_invite(
        self,
        guardian_user_id: str,
        invite_id: str,
    ) -> dict:
        """Reject a guardian invitation."""
        guardian_uuid = UUID(guardian_user_id)
        invite_uuid = UUID(invite_id)

        invite = await self._guardian_repo.get_invite_by_id(invite_uuid)
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "GUARDIAN.INVITE.NOT_FOUND", "message": "Invitation not found"},
            )

        guardian_user = await self._auth_repo.get_user_by_id(guardian_uuid)
        if not guardian_user or guardian_user.email != invite.guardian_email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "GUARDIAN.INVITE.FORBIDDEN",
                    "message": "This invitation is not for you",
                },
            )

        if invite.rejected_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "GUARDIAN.INVITE.ALREADY_REJECTED",
                    "message": "Invitation already rejected",
                },
            )

        invite.rejected_at = datetime.now(timezone.utc).replace(tzinfo=None)

        logger.info(
            f"Guardian invite rejected: {invite.id}",
            extra={
                "invite_id": str(invite.id),
                "guardian_user_id": str(guardian_uuid),
            },
        )

        return {"status": "REJECTED"}

    async def remove_guardian(
        self,
        user_id: str,
        relationship_id: str,
    ) -> dict:
        """
        Remove a guardian relationship.
        
        Can be called by either blind user or guardian.
        """
        user_uuid = UUID(user_id)
        relationship_uuid = UUID(relationship_id)

        relationship = await self._guardian_repo.get_relationship_by_id(relationship_uuid)
        if not relationship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "GUARDIAN.RELATIONSHIP.NOT_FOUND",
                    "message": "Relationship not found",
                },
            )

        # Verify user is part of this relationship
        if relationship.blind_user_id != user_uuid and relationship.guardian_user_id != user_uuid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "GUARDIAN.RELATIONSHIP.FORBIDDEN",
                    "message": "You are not part of this relationship",
                },
            )

        await self._guardian_repo.update_relationship_status(
            relationship_uuid, GuardianStatus.REMOVED.value
        )

        logger.info(
            f"Guardian relationship removed: {relationship_id}",
            extra={
                "relationship_id": relationship_id,
                "user_id": user_id,
            },
        )

        return {"status": "REMOVED"}

    async def get_my_guardians(self, blind_user_id: str) -> list[dict]:
        """Get all guardians for a blind user."""
        blind_uuid = UUID(blind_user_id)
        relationships = await self._guardian_repo.get_guardians_for_user(blind_uuid)

        result = []
        for rel in relationships:
            guardian = await self._auth_repo.get_user_by_id(rel.guardian_user_id)
            if guardian:
                result.append({
                    "id": str(rel.id),
                    "guardian_email": guardian.email,
                    "status": rel.status,
                    "permissions": rel.permissions,
                    "accepted_at": rel.accepted_at.isoformat() if rel.accepted_at else None,
                    "created_at": rel.created_at.isoformat(),
                })

        return result

    async def get_my_blind_users(self, guardian_user_id: str) -> list[dict]:
        """Get all blind users monitored by a guardian."""
        guardian_uuid = UUID(guardian_user_id)
        relationships = await self._guardian_repo.get_blind_users_for_guardian(guardian_uuid)

        result = []
        for rel in relationships:
            blind_user = await self._auth_repo.get_user_by_id(rel.blind_user_id)
            if blind_user:
                result.append({
                    "id": str(blind_user.id),
                    "email": blind_user.email,
                    "relationship_id": str(rel.id),
                    "permissions": rel.permissions,
                })

        return result
