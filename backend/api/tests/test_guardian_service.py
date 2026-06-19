"""Tests for guardian service."""
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.modules.guardian.service import GuardianService
from app.modules.guardian.models import GuardianStatus


class MockAuthRepository:
    """Mock auth repository for testing."""

    def __init__(self):
        self.users = {}

    def add_user(self, user_id, email, roles, phone_number=None):
        from app.modules.auth.models import User
        user = User(id=user_id, email=email, password_hash="test", roles=roles, phone_number=phone_number)
        self.users[user_id] = user
        return user

    async def get_user_by_id(self, user_id):
        return self.users.get(user_id)

    async def get_user_by_email(self, email):
        for user in self.users.values():
            if user.email == email:
                return user
        return None


class MockGuardianRepository:
    """Mock guardian repository for testing."""

    def __init__(self):
        self.invites = {}
        self.relationships = {}

    async def create_invite(self, blind_user_id, guardian_email, expires_at):
        from app.modules.guardian.models import GuardianInvite
        invite = GuardianInvite(
            id=uuid4(),
            blind_user_id=blind_user_id,
            guardian_email=guardian_email,
            expires_at=expires_at,
        )
        self.invites[invite.id] = invite
        return invite

    async def get_invite_by_id(self, invite_id):
        return self.invites.get(invite_id)

    async def get_pending_invite(self, blind_user_id, guardian_email):
        for invite in self.invites.values():
            if (
                invite.blind_user_id == blind_user_id
                and invite.guardian_email == guardian_email
                and not invite.accepted_at
                and not invite.rejected_at
            ):
                return invite
        return None

    async def create_relationship(self, blind_user_id, guardian_user_id, permissions):
        from app.modules.guardian.models import GuardianRelationship
        relationship = GuardianRelationship(
            id=uuid4(),
            blind_user_id=blind_user_id,
            guardian_user_id=guardian_user_id,
            status=GuardianStatus.ACTIVE.value,
            permissions=permissions,
            accepted_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        self.relationships[relationship.id] = relationship
        return relationship

    async def get_active_relationship(self, blind_user_id, guardian_user_id):
        for rel in self.relationships.values():
            if (
                rel.blind_user_id == blind_user_id
                and rel.guardian_user_id == guardian_user_id
                and rel.status == GuardianStatus.ACTIVE.value
            ):
                return rel
        return None

    async def get_guardians_for_user(self, blind_user_id):
        return [r for r in self.relationships.values() if r.blind_user_id == blind_user_id]


class MockNotificationService:
    """Mock notification service for testing."""

    def __init__(self):
        self.sent_invites = []
        self.sent_sos = []

    async def send_guardian_invite(self, recipient_email, recipient_phone, blind_user_email, invite_id):
        self.sent_invites.append({
            "recipient_email": recipient_email,
            "blind_user_email": blind_user_email,
            "invite_id": invite_id,
        })


@pytest.fixture
def auth_repo():
    return MockAuthRepository()


@pytest.fixture
def guardian_repo():
    return MockGuardianRepository()


@pytest.fixture
def notification_service():
    return MockNotificationService()


@pytest.fixture
def guardian_service(auth_repo, guardian_repo, notification_service):
    return GuardianService(guardian_repo, auth_repo, notification_service)


@pytest.mark.asyncio
async def test_invite_guardian_success(guardian_service, auth_repo):
    """Test successful guardian invitation."""
    # Setup users
    blind_user_id = uuid4()
    guardian_user_id = uuid4()

    auth_repo.add_user(blind_user_id, "blind@example.com", ["blind"])
    auth_repo.add_user(guardian_user_id, "guardian@example.com", ["family"])

    # Invite guardian
    result = await guardian_service.invite_guardian(
        blind_user_id=str(blind_user_id),
        guardian_email="guardian@example.com",
        permissions=["VIEW_LOCATION", "RECEIVE_SOS"],
    )

    assert result["status"] == "PENDING"
    assert result["guardian_email"] == "guardian@example.com"
    assert "invite_id" in result
    assert "expires_at" in result


@pytest.mark.asyncio
async def test_invite_guardian_nonexistent_guardian(guardian_service, auth_repo):
    """Test inviting a non-existent guardian."""
    blind_user_id = uuid4()
    auth_repo.add_user(blind_user_id, "blind@example.com", ["blind"])

    with pytest.raises(Exception) as exc_info:
        await guardian_service.invite_guardian(
            blind_user_id=str(blind_user_id),
            guardian_email="nonexistent@example.com",
            permissions=["VIEW_LOCATION"],
        )

    assert "does not exist" in str(exc_info.value.detail["message"])


@pytest.mark.asyncio
async def test_accept_invite_success(guardian_service, auth_repo, guardian_repo):
    """Test successful invitation acceptance."""
    # Setup users
    blind_user_id = uuid4()
    guardian_user_id = uuid4()

    auth_repo.add_user(blind_user_id, "blind@example.com", ["blind"])
    auth_repo.add_user(guardian_user_id, "guardian@example.com", ["family"])

    # Create invite manually
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
    invite = await guardian_repo.create_invite(
        blind_user_id=blind_user_id,
        guardian_email="guardian@example.com",
        expires_at=expires_at,
    )

    # Accept invite
    result = await guardian_service.accept_invite(
        guardian_user_id=str(guardian_user_id),
        invite_id=str(invite.id),
    )

    assert result["status"] == "ACTIVE"
    assert "relationship_id" in result
    assert "permissions" in result


@pytest.mark.asyncio
async def test_accept_expired_invite(guardian_service, auth_repo, guardian_repo):
    """Test accepting an expired invitation."""
    blind_user_id = uuid4()
    guardian_user_id = uuid4()

    auth_repo.add_user(blind_user_id, "blind@example.com", ["blind"])
    auth_repo.add_user(guardian_user_id, "guardian@example.com", ["family"])

    # Create expired invite
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    invite = await guardian_repo.create_invite(
        blind_user_id=blind_user_id,
        guardian_email="guardian@example.com",
        expires_at=expires_at,
    )

    # Try to accept
    with pytest.raises(Exception) as exc_info:
        await guardian_service.accept_invite(
            guardian_user_id=str(guardian_user_id),
            invite_id=str(invite.id),
        )

    assert "expired" in str(exc_info.value.detail["message"]).lower()
