"""Pydantic models for service health checks."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ServiceHealthDetail(BaseModel):
    status: str = Field(..., description="Service status (e.g. connected, disconnected, operational)")
    engine: str | None = None
    note: str | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall platform status ('ok', 'degraded', 'error')")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Environment (development, staging, production)")
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    services: dict[str, Any] = Field(..., description="Subsystem health statuses")
