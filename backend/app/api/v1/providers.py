"""API Endpoints for Doctor, Clinic & Hospital Discovery and Provider Verification."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, log_audit_event, require_role
from app.core.logging import logger
from app.models.user import User
from app.providers.geocoding import CompositeGeoProvider
from app.providers.schemas import (
    DoctorDetail,
    FacilityDetail,
    GeocodeResult,
    IngestionStats,
    ProviderSearchResponse,
    SpecialtiesResponse,
)
from app.providers.seeder import ProviderSeeder
from app.providers.service import ProviderService

router = APIRouter()
provider_service = ProviderService()
geocoder = CompositeGeoProvider(allow_network=False)


@router.get(
    "/search",
    response_model=ProviderSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search Doctors, Clinics & Hospitals",
    description=(
        "Executes multi-criteria geographic and specialty search over verified and listed healthcare providers. "
        "Supports PostGIS distance calculation, radius filtering, open-now filtering, and red-flag emergency detection."
    ),
)
async def search_providers(
    request: Request,
    query: str | None = Query(None, description="Search term (Doctor name, facility, specialty, or locality)"),
    lat: float | None = Query(None, ge=-90.0, le=90.0, description="User latitude for distance sorting"),
    lon: float | None = Query(None, ge=-180.0, le=180.0, description="User longitude for distance sorting"),
    radius_km: float = Query(10.0, ge=0.5, le=100.0, description="Search radius in kilometers (max 100km)"),
    city: str | None = Query(None, description="City name (e.g., Chennai, Bengaluru, Kochi)"),
    state: str | None = Query(None, description="State name (e.g., Tamil Nadu, Karnataka)"),
    specialty: str | None = Query(None, description="Medical specialty filter"),
    provider_type: str | None = Query(
        "all",
        description="Filter by type: 'all', 'doctor', 'facility', 'hospital', 'clinic', 'health_center', 'dispensary'",
    ),
    verification_status: str | None = Query(
        None,
        description="Filter by verification tier: 'VERIFIED', 'PARTIALLY_VERIFIED', 'UNVERIFIED', 'DEMO_SIMULATED'",
    ),
    open_now: bool | None = Query(None, description="Filter for providers open at current local time"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=50, description="Page size (max 50)"),
    language: str = Query("en", description="User language code ('en', 'ta', 'hi', 'ml', 'te', 'kn')"),
    db: AsyncSession = Depends(get_db),
) -> ProviderSearchResponse:
    try:
        response = await provider_service.search_providers(
            db=db,
            query=query,
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            city=city,
            state=state,
            specialty=specialty,
            provider_type=provider_type,
            verification_status=verification_status,
            open_now=open_now,
            page=page,
            page_size=page_size,
            language=language,
        )
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        ) from val_err

    # Privacy-conscious audit logging: log filter metadata without storing exact user coordinates
    try:
        await log_audit_event(
            db=db,
            action="PROVIDER_SEARCH",
            user_id=None,
            request=request,
            details={
                "has_query": bool(query),
                "city": city,
                "specialty": specialty,
                "provider_type": provider_type,
                "radius_km": radius_km,
                "results_count": response.total,
                "has_emergency_alert": bool(response.emergency_escalation),
            },
        )
    except Exception as e:
        logger.warning(f"Audit log skipped for provider search: {e}")

    return response


@router.get(
    "/nearby",
    response_model=ProviderSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Discover Nearby Healthcare Providers",
    description="Requires user geographic coordinates and returns nearby doctors and facilities sorted by proximity.",
)
async def get_nearby_providers(
    request: Request,
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude"),
    radius_km: float = Query(10.0, ge=0.5, le=100.0, description="Search radius in kilometers"),
    specialty: str | None = Query(None, description="Specialty filter"),
    provider_type: str | None = Query("all", description="Provider type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    language: str = Query("en"),
    db: AsyncSession = Depends(get_db),
) -> ProviderSearchResponse:
    return await provider_service.search_providers(
        db=db,
        query=None,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        specialty=specialty,
        provider_type=provider_type,
        page=page,
        page_size=page_size,
        language=language,
    )


@router.get(
    "/specialties",
    response_model=SpecialtiesResponse,
    status_code=status.HTTP_200_OK,
    summary="List Medical Specialties",
    description="Returns available clinical specialties with counts of associated healthcare practitioners.",
)
async def list_specialties(db: AsyncSession = Depends(get_db)) -> SpecialtiesResponse:
    return await provider_service.get_specialties_summary(db=db)


@router.get(
    "/facilities/{facility_id}",
    response_model=FacilityDetail,
    status_code=status.HTTP_200_OK,
    summary="Get Healthcare Facility Details",
    description="Retrieves comprehensive facility profile, address, operating hours, and affiliated doctors.",
)
async def get_facility_details(
    facility_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FacilityDetail:
    facility = await provider_service.get_facility_details(db=db, facility_id=facility_id)
    if not facility:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Healthcare facility with ID {facility_id} not found.",
        )
    return facility


@router.get(
    "/doctors/{doctor_id}",
    response_model=DoctorDetail,
    status_code=status.HTTP_200_OK,
    summary="Get Doctor Profile Details",
    description="Retrieves detailed doctor profile, qualifications, registration council, and affiliated clinic schedules.",
)
async def get_doctor_details(
    doctor_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DoctorDetail:
    doctor = await provider_service.get_doctor_details(db=db, doctor_id=doctor_id)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor profile with ID {doctor_id} not found.",
        )
    return doctor


@router.get(
    "/geocode",
    response_model=GeocodeResult,
    status_code=status.HTTP_200_OK,
    summary="Geocode City or Locality Name",
    description="Resolves city or locality query into latitude, longitude, and geographic attribution.",
)
async def geocode_location(
    query: str = Query(..., min_length=2, description="Place name or address"),
) -> GeocodeResult:
    res = await geocoder.geocode(query)
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Location '{query}' could not be resolved. Please verify spelling or provide coordinates.",
        )
    return res


@router.post(
    "/seed",
    response_model=IngestionStats,
    status_code=status.HTTP_200_OK,
    summary="Admin Seed / Reindex Provider Dataset",
    description="Restricted administrative endpoint to ingest or synchronize canonical seed providers into PostGIS.",
)
async def seed_provider_dataset(
    request: Request,
    force_reload: bool = Query(False, description="Whether to overwrite existing records"),
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> IngestionStats:
    stats = await ProviderSeeder.seed(db=db, force_reload=force_reload)

    await log_audit_event(
        db=db,
        action="ADMIN_PROVIDER_SEED",
        user_id=current_user.id,
        request=request,
        details={
            "facilities": stats.facilities_ingested,
            "doctors": stats.doctors_ingested,
            "affiliations": stats.affiliations_ingested,
        },
    )

    return stats
