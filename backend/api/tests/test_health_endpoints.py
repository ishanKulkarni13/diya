import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config.settings import settings

client = TestClient(app)

def test_live_endpoint():
    response = client.get("/api/v1/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

@patch("app.api.health.get_db")
def test_ready_endpoint_success(mock_get_db):
    # This is an integration test using TestClient, but since we rely on Depends(get_db)
    # we need to override the dependency in the app.
    pass

# We can use app.dependency_overrides
from app.db.session import get_db

@pytest.fixture
def mock_db_session():
    session = MagicMock()
    # async mocks
    import asyncio
    future = asyncio.Future()
    future.set_result(True)
    session.execute.return_value = future
    return session

def test_ready_endpoint_ok(mock_db_session):
    async def override_get_db():
        yield mock_db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    with patch.object(settings.providers, 'gemini_api_key', 'test-key'):
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "ok", "gemini": "ok"}
        
    app.dependency_overrides.clear()

def test_ready_endpoint_degraded_gemini(mock_db_session):
    async def override_get_db():
        yield mock_db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    with patch.object(settings.providers, 'gemini_api_key', None):
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "ok", "gemini": "degraded"}
        
    app.dependency_overrides.clear()

def test_ready_endpoint_db_failure(mock_db_session):
    mock_db_session.execute.side_effect = Exception("DB Connection failed")
    
    async def override_get_db():
        yield mock_db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "HEALTH.NOT_READY"
    assert response.json()["error"]["details"]["database"] == "unreachable"
    
    app.dependency_overrides.clear()
