"""Database models for Regional Health Alerts, Advisories, and Epidemiological Notifications."""

import enum
import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AlertSeverity(str, enum.Enum):
    """Clinical and public health urgency level."""

    CRITICAL = "CRITICAL"            # Severe outbreak or hazard requiring immediate public action
    HIGH = "HIGH"                    # Rapidly spreading epidemic, toxic air quality, heatwave red alert
    MODERATE = "MODERATE"            # Localized seasonal outbreak, water safety notice, preventive advisory
    LOW = "LOW"                      # General preventive health notice, mild seasonal guidance
    INFORMATIONAL = "INFORMATIONAL"   # Vaccination camp, health awareness drive, administrative bulletin


class AlertStatus(str, enum.Enum):
    """Lifecycle state of the public health alert."""

    ACTIVE = "ACTIVE"                # Currently in effect and within validity window
    EXPIRED = "EXPIRED"              # Superseded or past validity date
    DRAFT = "DRAFT"                  # Unreleased administrative draft
    INFORMATIONAL = "INFORMATIONAL"   # Non-urgent standing educational/public guideline


class AlertCategory(str, enum.Enum):
    """Public health epidemiological domain."""

    INFECTIOUS_DISEASE = "infectious_disease"
    OUTBREAK = "outbreak"
    SEASONAL_EPIDEMIC = "seasonal_epidemic"
    ENVIRONMENTAL_HAZARD = "environmental_hazard"
    AIR_QUALITY = "air_quality"
    FOOD_WATER_SAFETY = "food_water_safety"
    HEATWAVE = "heatwave"
    VACCINATION_DRIVE = "vaccination_drive"
    PUBLIC_HEALTH_ADVISORY = "public_health_advisory"


class HealthAlert(Base):
    """Regional Health Alert and Public Health Advisory entity."""

    __tablename__ = "health_alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default=AlertCategory.PUBLIC_HEALTH_ADVISORY.value, nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(
        String(50), default=AlertSeverity.MODERATE.value, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default=AlertStatus.ACTIVE.value, nullable=False, index=True
    )

    # Trusted Public Health Source & Provenance Metadata
    source_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(500), nullable=False)
    source_reference_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Geographic Targeting
    country: Mapped[str] = mapped_column(String(50), default="India", nullable=False)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)  # None or ALL_INDIA = national
    district: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    locality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    affected_radius_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    geom = mapped_column(
        Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True), nullable=True
    )

    # Multilingual Content & Clinical Action Directives
    translations: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    symptoms: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    precautionary_measures: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    helpline_numbers: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Demonstration Guardrail & Provenance
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    provenance_audit: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
