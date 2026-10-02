"""Pydantic V2 Schemas for Provider Discovery, Search, and Verification."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.rag.models import EmergencyEscalation


class LocationCoordinates(BaseModel):
    """Geographic coordinates schema."""

    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in decimal degrees")


class AddressInfo(BaseModel):
    """Structured provider postal address."""

    address_line1: str
    address_line2: str | None = None
    locality: str | None = None
    city: str
    state: str
    pincode: str
    country: str = "India"


class VerificationBadge(BaseModel):
    """Verification metadata and badge presentation."""

    status: str = Field(..., description="Effective verification status: DEMO_SIMULATED | VERIFIED | PARTIALLY_VERIFIED | UNVERIFIED")
    tier: str = Field(..., description="Effective tier: tier_4_demo | tier_1_verified | tier_2_partially_verified | tier_3_unverified")
    effective_status: str = Field(..., description="Effective display/verification status (strictly DEMO_SIMULATED when is_demo_data=True)")
    effective_tier: str = Field(..., description="Effective tier: tier_4_demo when is_demo_data=True")
    simulated_target_status: str | None = Field(default=None, description="Target verification status simulated in synthetic environment")
    simulated_target_tier: str | None = Field(default=None, description="Target tier simulated in synthetic environment")
    label: str = Field(..., description="User-facing badge label")
    description: str = Field(..., description="Detailed explanation of verification method and provenance")
    source: str | None = None
    method: str | None = None
    verified_at: datetime | None = None
    is_demo_data: bool = True


class FacilitySummary(BaseModel):
    """Concise representation of a healthcare facility."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    facility_type: str
    city: str
    state: str
    pincode: str
    locality: str | None = None
    latitude: float
    longitude: float
    distance_km: float | None = None
    emergency_services_available: bool = False
    verification: VerificationBadge
    effective_status: str = Field("DEMO_SIMULATED", description="Effective display/verification status")
    is_demo_data: bool = True


class FacilityDetail(BaseModel):
    """Detailed healthcare facility entity with contact and affiliated physicians."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    facility_type: str
    address: AddressInfo
    location: LocationCoordinates
    distance_km: float | None = None
    phone: str | None = None
    emergency_phone: str | None = None
    email: str | None = None
    website: str | None = None
    operating_hours: dict[str, Any] | None = None
    emergency_services_available: bool = False
    verification: VerificationBadge
    effective_status: str = Field("DEMO_SIMULATED", description="Effective display/verification status")
    is_demo_data: bool = True
    source_name: str
    source_url: str | None = None
    affiliated_doctors: list["DoctorSummary"] = []
    created_at: datetime
    updated_at: datetime


class DoctorSummary(BaseModel):
    """Concise summary of a physician / healthcare specialist."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    qualifications: str
    primary_specialty: str
    experience_years: int | None = None
    languages_spoken: list[str] = []
    consultation_fee: float | None = None
    primary_facility_id: UUID | None = None
    primary_facility_name: str | None = None
    facility_type: str | None = None
    city: str | None = None
    state: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    distance_km: float | None = None
    verification: VerificationBadge
    effective_status: str = Field("DEMO_SIMULATED", description="Effective display/verification status")
    is_demo_data: bool = True


class DoctorDetail(BaseModel):
    """Detailed physician entity including council registration and affiliations."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    gender: str | None = None
    qualifications: str
    primary_specialty: str
    secondary_specialties: list[str] = []
    registration_number: str | None = None
    registration_council: str | None = None
    experience_years: int | None = None
    languages_spoken: list[str] = []
    consultation_fee: float | None = None
    bio: str | None = None
    verification: VerificationBadge
    effective_status: str = Field("DEMO_SIMULATED", description="Effective display/verification status")
    is_demo_data: bool = True
    source_name: str
    source_url: str | None = None
    affiliations: list[dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime


class ProviderCard(BaseModel):
    """Unified presentation card for search results (Doctor or Facility)."""

    card_type: str = Field(..., description="'doctor' or 'facility'")
    id: UUID
    title: str
    subtitle: str
    facility_name: str | None = None
    facility_type: str | None = None
    specialty: str | None = None
    qualifications: str | None = None
    experience_years: int | None = None
    address_line: str
    city: str
    state: str
    latitude: float
    longitude: float
    distance_km: float | None = None
    phone: str | None = None
    emergency_services_available: bool = False
    languages_spoken: list[str] = []
    operating_hours: dict[str, Any] | None = None
    verification: VerificationBadge
    effective_status: str = Field("DEMO_SIMULATED", description="Effective display/verification status")
    is_demo_data: bool = True


class ProviderSearchResponse(BaseModel):
    """Structured response for provider discovery queries."""

    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[ProviderCard]
    emergency_escalation: EmergencyEscalation | None = None
    applied_filters: dict[str, Any]
    disclaimer: str


class SpecialtyItem(BaseModel):
    """Specialty name with provider availability count."""

    specialty: str
    count: int


class SpecialtiesResponse(BaseModel):
    """List of all available medical specialties."""

    specialties: list[SpecialtyItem]


class GeocodeResult(BaseModel):
    """Geocoding lookup result with attribution."""

    query: str
    display_name: str
    latitude: float
    longitude: float
    city: str | None = None
    state: str | None = None
    country: str = "India"
    provider: str
    attribution: str


class IngestionStats(BaseModel):
    """Provider data ingestion statistics."""

    status: str
    facilities_ingested: int
    doctors_ingested: int
    affiliations_ingested: int
    is_demo_data: bool
    message: str
