"""Doctor, Clinic, Hospital, and Provider Verification Database Models."""

import enum
import uuid
from datetime import datetime
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class VerificationStatus(str, enum.Enum):
    """Explicit verification status for healthcare providers and facilities."""

    VERIFIED = "VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    DEMO_SIMULATED = "DEMO_SIMULATED"


class VerificationTier(str, enum.Enum):
    """Provider verification tier indicating authority level."""

    TIER_1_VERIFIED = "tier_1_verified"
    TIER_2_PARTIALLY_VERIFIED = "tier_2_partially_verified"
    TIER_3_UNVERIFIED = "tier_3_unverified"
    TIER_4_DEMO = "tier_4_demo"


class FacilityType(str, enum.Enum):
    """Class of medical establishment."""

    HOSPITAL = "hospital"
    CLINIC = "clinic"
    HEALTH_CENTER = "health_center"
    DISPENSARY = "dispensary"
    DIAGNOSTIC_CENTER = "diagnostic_center"
    PHARMACY = "pharmacy"


class Facility(Base):
    """Healthcare facility entity (hospital, clinic, health center, dispensary)."""

    __tablename__ = "facilities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    facility_type: Mapped[str] = mapped_column(
        String(50), default=FacilityType.CLINIC.value, nullable=False, index=True
    )
    address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locality: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pincode: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    country: Mapped[str] = mapped_column(String(50), default="India", nullable=False)

    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    geom: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    emergency_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    operating_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    emergency_services_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Verification & Provenance Metadata
    verification_status: Mapped[str] = mapped_column(
        String(50), default=VerificationStatus.DEMO_SIMULATED.value, nullable=False, index=True
    )
    verification_tier: Mapped[str] = mapped_column(
        String(50), default=VerificationTier.TIER_4_DEMO.value, nullable=False
    )
    verification_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(
        String(255), default="ClintelAI Internal Dataset", nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    doctor_affiliations: Mapped[list["DoctorAffiliation"]] = relationship(
        "DoctorAffiliation",
        back_populates="facility",
        cascade="all, delete-orphan",
    )


class Doctor(Base):
    """Healthcare professional entity (physicians, specialists, consultants)."""

    __tablename__ = "doctors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    qualifications: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_specialty: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    secondary_specialties: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    registration_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    registration_council: Mapped[str | None] = mapped_column(String(150), nullable=True)
    experience_years: Mapped[int | None] = mapped_column(Integer, nullable=True)
    languages_spoken: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    consultation_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Verification & Provenance Metadata
    verification_status: Mapped[str] = mapped_column(
        String(50), default=VerificationStatus.DEMO_SIMULATED.value, nullable=False, index=True
    )
    verification_tier: Mapped[str] = mapped_column(
        String(50), default=VerificationTier.TIER_4_DEMO.value, nullable=False
    )
    verification_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    verification_method: Mapped[str | None] = mapped_column(String(100), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    source_name: Mapped[str] = mapped_column(
        String(255), default="ClintelAI Internal Dataset", nullable=False
    )
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    affiliations: Mapped[list["DoctorAffiliation"]] = relationship(
        "DoctorAffiliation",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )


class DoctorAffiliation(Base):
    """Junction entity associating doctors with healthcare facilities and clinical schedules."""

    __tablename__ = "doctor_affiliations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_or_designation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    schedule: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="affiliations")
    facility: Mapped["Facility"] = relationship("Facility", back_populates="doctor_affiliations")
