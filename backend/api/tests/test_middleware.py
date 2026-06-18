import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware import RequestLoggingMiddleware
from app.config.logging import request_id_ctx

app = FastAPI()
app.add_middleware(RequestLoggingMiddleware)

@app.get("/test")
async def dummy_endpoint():
    request_id = request_id_ctx.get()
    return {"request_id": request_id}

@app.get("/error")
async def dummy_error_endpoint():
    raise ValueError("Test error")

client = TestClient(app)

def test_middleware_adds_request_id():
    response = client.get("/test")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    
    data = response.json()
    assert data["request_id"] == response.headers["x-request-id"]

def test_middleware_uses_provided_request_id():
    response = client.get("/test", headers={"X-Request-ID": "custom-id-123"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "custom-id-123"
    assert response.json()["request_id"] == "custom-id-123"

def test_middleware_handles_errors():
    with pytest.raises(ValueError):
        client.get("/error")
