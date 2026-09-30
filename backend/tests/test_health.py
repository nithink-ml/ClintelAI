"""Tests for the health check endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_liveness_probe():
    """Verify /healthz returns 200 with alive status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["app"] == settings.PROJECT_NAME


@pytest.mark.asyncio
async def test_api_v1_health_endpoint():
    """Verify /api/v1/health returns detailed health response."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"{settings.API_V1_STR}/health")
        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "status" in data
        assert data["app_name"] == settings.PROJECT_NAME
        assert data["version"] == settings.VERSION
        assert data["environment"] == settings.ENVIRONMENT
        assert "timestamp" in data
        assert "services" in data

        # Check services map
        services = data["services"]
        assert "api" in services
        assert services["api"]["status"] == "operational"
        assert "database" in services
        assert "redis" in services
        assert "llm_provider" in services
        assert "vector_store" in services
