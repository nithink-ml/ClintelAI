"""Pydantic V2 Schemas for Regional Health Alerts, Ingestion, and Multilingual Syndication."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models import EmergencyEscalation


class FreshnessStatus(BaseModel):
    """Temporal freshness evaluation for public health bulletins."""

    status: str = Field(..., description="FRESH (<24h) | RECENT (<7d) | STALE (>7d) | EXPIRED")
    age_hours: float
    last_verified_at: datetime
    notice: str = Field(..., description="Human-readable freshness notice and verification instruction")


class LocalizedAlertContent(BaseModel):
    """Translated alert text for specific locale."""

    title: str
    summary: str
    content: str
    precautionary_measures: list[str] = []


class HealthAlertSummary(BaseModel):
    """Concise health alert entity for list views, map feeds, and dashboard banners."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str
    category: str = Field(..., description="infectious_disease | outbreak | seasonal_epidemic | air_quality | etc.")
    severity: str = Field(..., description="CRITICAL | HIGH | MODERATE | LOW | INFORMATIONAL")
    status: str = Field(..., description="ACTIVE | EXPIRED | DRAFT | INFORMATIONAL")
    source_name: str
    source_url: str
    source_reference_id: str | None = None
    issued_at: datetime
    valid_from: datetime
    valid_until: datetime | None = None
    country: str = "India"
    state: str | None = None
    district: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    affected_radius_km: float | None = None
    distance_km: float | None = None
    freshness: FreshnessStatus
    is_demo_data: bool = True


class HealthAlertDetail(BaseModel):
    """Comprehensive health alert dossier with clinical guidelines, helplines, and translations."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str
    content: str
    category: str
    severity: str
    status: str
    source_name: str
    source_url: str
    source_reference_id: str | None = None
    issued_at: datetime
    valid_from: datetime
    valid_until: datetime | None = None
    country: str = "India"
    state: str | None = None
    district: str | None = None
    city: str | None = None
    locality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    affected_radius_km: float | None = None
    symptoms: list[str] = []
    precautionary_measures: list[str] = []
    helpline_numbers: list[str] = []
    translations: dict[str, Any] | None = None
    freshness: FreshnessStatus
    is_demo_data: bool = True
    provenance_audit: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class HealthAlertSearchResponse(BaseModel):
    """Structured response for regional health alert queries."""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[HealthAlertSummary]
    critical_active_count: int = 0
    emergency_escalation: EmergencyEscalation | None = None
    applied_filters: dict[str, Any]
    disclaimer: str


class HealthAlertCreateRequest(BaseModel):
    """Administrative alert creation payload with strict trusted source validation."""

    title: str = Field(..., min_length=5, max_length=255)
    summary: str = Field(..., min_length=10)
    content: str = Field(..., min_length=20)
    category: str = Field(
        ...,
        description="infectious_disease | outbreak | seasonal_epidemic | environmental_hazard | air_quality | food_water_safety | heatwave | vaccination_drive | public_health_advisory",
    )
    severity: str = Field(..., description="CRITICAL | HIGH | MODERATE | LOW | INFORMATIONAL")
    status: str = Field(default="ACTIVE", description="ACTIVE | EXPIRED | DRAFT | INFORMATIONAL")
    source_name: str = Field(..., min_length=3, max_length=255)
    source_url: str = Field(..., min_length=10, max_length=500)
    source_reference_id: str | None = None
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_from: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime | None = None
    country: str = "India"
    state: str | None = None
    district: str | None = None
    city: str | None = None
    locality: str | None = None
    latitude: float | None = Field(None, ge=-90.0, le=90.0)
    longitude: float | None = Field(None, ge=-180.0, le=180.0)
    affected_radius_km: float | None = Field(None, ge=0.5, le=1000.0)
    symptoms: list[str] = []
    precautionary_measures: list[str] = []
    helpline_numbers: list[str] = []
    translations: dict[str, Any] | None = None
    is_demo_data: bool = True


class HealthAlertUpdateRequest(BaseModel):
    """Administrative partial alert update."""

    title: str | None = None
    summary: str | None = None
    content: str | None = None
    category: str | None = None
    severity: str | None = None
    status: str | None = None
    valid_until: datetime | None = None
    precautionary_measures: list[str] | None = None
    helpline_numbers: list[str] | None = None
    translations: dict[str, Any] | None = None
