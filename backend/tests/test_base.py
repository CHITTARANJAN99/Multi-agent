import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.settings import settings

client = TestClient(app)

def test_health_endpoint():
    """Verify that the health check endpoint returns 200 and indicates healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == settings.APP_NAME

def test_settings_loading():
    """Verify settings properties load correctly from configurations."""
    assert settings.APP_NAME == "Universal Multi-Agent AI Assistant"
    assert settings.API_V1_STR == "/api"
    # Verify async database url parser mapping
    assert "postgresql+asyncpg" in settings.async_database_url

def test_auth_endpoints_missing_token():
    """Verify that protected endpoints raise a 401 Unauthorized status code without a token."""
    response = client.get(f"{settings.API_V1_STR}/mcp/tools")
    assert response.status_code == 401
    assert "error" in response.json()
    assert response.json()["error"] == "AuthenticationError"
