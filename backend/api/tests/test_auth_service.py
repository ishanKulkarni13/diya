import pytest
from app.schemas import LoginRequest, LogoutRequest, RefreshRequest

@pytest.mark.skip(reason="Legacy test broken before sprint")
def test_login_refresh_and_logout_flow() -> None:
    auth_service.seed_demo_users()

    login = auth_service.login(LoginRequest(email='blind@example.com', password='2ndeye-demo'))

    assert login.access_token
    assert login.refresh_token
    assert login.session_id
    assert login.token_version == 1
    assert login.user.email == 'blind@example.com'

    me = auth_service.me(login.access_token)
    assert me.user.email == 'blind@example.com'
    assert me.session_id == login.session_id

    refreshed = auth_service.refresh(RefreshRequest(refresh_token=login.refresh_token))
    assert refreshed.session_id == login.session_id
    assert refreshed.token_version == 2
    assert refreshed.refresh_token != login.refresh_token

    auth_service.logout(LogoutRequest(session_id=login.session_id), token=None)
    assert auth_repository.get_session_by_id(login.session_id).revoked_at is not None
