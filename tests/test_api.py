"""Tests for FastAPI endpoints and health inspection."""

from fastapi.testclient import TestClient
from browserpilot.server.app import create_app


def test_api_health_endpoint() -> None:
    """Verify that /api/health returns valid system status."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"
        assert "llm_provider" in data


def test_api_status_idle() -> None:
    """Verify that /api/sessions/status reports idle when no mission is active."""
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/sessions/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "idle"
        assert data["total_steps"] == 0
