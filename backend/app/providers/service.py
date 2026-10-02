from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import String, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.provider import (
    Doctor,
    DoctorAffiliation,
    Facility,
    VerificationStatus,
    VerificationTier,
)
from app.providers.geocoding import CompositeGeoProvider
from app.providers.schemas import (
    AddressInfo,
    DoctorDetail,
    DoctorSummary,
    FacilityDetail,
    LocationCoordinates,
    ProviderCard,
    ProviderSearchResponse,
    SpecialtiesResponse,
    SpecialtyItem,
    VerificationBadge,
)
from app.rag.safety import MedicalSafetyEngine


class ProviderService:
    """Orchestrates location-based provider discovery, PostGIS distance calculations, and safety boundaries."""

    def __init__(self, geo_provider: CompositeGeoProvider | None = None):
        self.geocoder = geo_provider or CompositeGeoProvider(allow_network=False)

    @staticmethod
    def build_verification_badge(
        status: str,
        tier: str,
        source: str | None = None,
        method: str | None = None,
        verified_at: datetime | None = None,
        is_demo: bool = True,
    ) -> VerificationBadge:
        """Constructs a structured, transparent verification badge."""
        st_upper = status.upper() if status else VerificationStatus.DEMO_SIMULATED.value

        if is_demo:
            label = "DEMO / TEST LISTING"
            desc = (
                "Synthetic demonstration entry created strictly for algorithmic and UI verification. "
                "Do not use for real-world clinical appointments or emergency care."
            )
        elif st_upper == VerificationStatus.VERIFIED.value:
            label = "Officially Verified"
            desc = "Formally cross-referenced and verified against authoritative Medical Council or NABH registry."
        elif st_upper == VerificationStatus.PARTIALLY_VERIFIED.value:
            label = "Third-Party Listed"
            desc = "Confirmed via municipal register or OpenStreetMap directory; independent license verification pending."
        elif st_upper == VerificationStatus.UNVERIFIED.value:
            label = "Unverified Listing"
            desc = "Community-submitted record without official licensing verification. Exercise clinical discretion."
        else:
            label = "Simulated Record"
            desc = "Simulated record for testing purposes."

        return VerificationBadge(
            status=st_upper,
            tier=tier,
            label=label,
            description=desc,
            source=source,
            method=method,
            verified_at=verified_at,
            is_demo_data=is_demo,
        )

    async def search_providers(
        self,
        db: AsyncSession,
        query: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_km: float = 10.0,
        city: str | None = None,
        state: str | None = None,
        specialty: str | None = None,
        provider_type: str | None = None,
        verification_status: str | None = None,
        open_now: bool | None = None,
        page: int = 1,
        page_size: int = 10,
        language: str = "en",
    ) -> ProviderSearchResponse:
        """Executes combined spatial, specialty, and text search across doctors and facilities."""
        applied_filters: dict[str, Any] = {
            "query": query,
            "radius_km": radius_km,
            "city": city,
            "state": state,
            "specialty": specialty,
            "provider_type": provider_type or "all",
            "verification_status": verification_status,
            "open_now": open_now,
        }

        # 1. Emergency red-flag symptom screening
        emergency_escalation = None
        if query and query.strip():
            emergency_escalation = MedicalSafetyEngine.evaluate_emergency(query, language=language)
            if not emergency_escalation.is_emergency:
                emergency_escalation = None

        # 2. Geocoding resolution if coordinates omitted but locality/city given
        user_lat = lat
        user_lon = lon
        if (user_lat is None or user_lon is None) and (city or (query and len(query.strip()) >= 3)):
            geo_term = city or query
            if geo_term:
                geo_res = await self.geocoder.geocode(geo_term)
                if geo_res:
                    user_lat = geo_res.latitude
                    user_lon = geo_res.longitude
                    applied_filters["resolved_location"] = {
                        "display_name": geo_res.display_name,
                        "lat": user_lat,
                        "lon": user_lon,
                        "attribution": geo_res.attribution,
                    }

        # Validate coordinate boundaries if provided
        if user_lat is not None and user_lon is not None and not (-90.0 <= user_lat <= 90.0 and -180.0 <= user_lon <= 180.0):
            raise ValueError("Coordinates out of valid geographic range: lat [-90, 90], lon [-180, 180]")

        cards: list[ProviderCard] = []

        # 3. Search Facilities if provider_type is 'all', 'facility', or specific facility type
        include_facilities = (
            not provider_type
            or provider_type.lower() in ("all", "facility", "clinic", "hospital", "health_center", "dispensary")
        )
        include_doctors = not provider_type or provider_type.lower() in ("all", "doctor")

        if include_facilities:
            facility_cards = await self._search_facilities(
                db=db,
                query=query,
                user_lat=user_lat,
                user_lon=user_lon,
                radius_km=radius_km,
                city=city,
                state=state,
                facility_type=provider_type if provider_type and provider_type.lower() not in ("all", "facility") else None,
                verification_status=verification_status,
                open_now=open_now,
            )
            cards.extend(facility_cards)

        if include_doctors:
            doctor_cards = await self._search_doctors(
                db=db,
                query=query,
                user_lat=user_lat,
                user_lon=user_lon,
                radius_km=radius_km,
                city=city,
                state=state,
                specialty=specialty,
                verification_status=verification_status,
            )
            cards.extend(doctor_cards)

        # 4. Sorting & Ranking
        # Priority: Distance (if location known), then Verification tier (verified first), then name
        def sort_key(card: ProviderCard) -> tuple[float, int, str]:
            dist = card.distance_km if card.distance_km is not None else 99999.0
            tier_rank = {
                VerificationTier.TIER_1_VERIFIED.value: 1,
                VerificationTier.TIER_2_PARTIALLY_VERIFIED.value: 2,
                VerificationTier.TIER_3_UNVERIFIED.value: 3,
                VerificationTier.TIER_4_DEMO.value: 4,
            }.get(card.verification.tier, 5)
            return (dist, tier_rank, card.title)

        cards.sort(key=sort_key)

        # 5. Pagination
        total = len(cards)
        page = max(1, page)
        page_size = max(1, min(50, page_size))
        total_pages = max(1, (total + page_size - 1) // page_size)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = cards[start_idx:end_idx]

        disclaimer = (
            "Notice: ClintelAI Provider Discovery provides factual, unranked healthcare directory listings "
            "based on verified registrations and public directories. ClintelAI does not endorse or rank providers by clinical skill. "
            "Always independently verify credentials. In medical emergencies, immediately dial 112 or 108."
        )

        return ProviderSearchResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=paginated_items,
            emergency_escalation=emergency_escalation,
            applied_filters=applied_filters,
            disclaimer=disclaimer,
        )

    async def _search_facilities(
        self,
        db: AsyncSession,
        query: str | None = None,
        user_lat: float | None = None,
        user_lon: float | None = None,
        radius_km: float = 10.0,
        city: str | None = None,
        state: str | None = None,
        facility_type: str | None = None,
        verification_status: str | None = None,
        open_now: bool | None = None,
    ) -> list[ProviderCard]:
        """Queries facilities using PostGIS spatial distances and filters."""
        stmt = select(Facility)

        # Spatial Point construction in WGS84
        dist_expr = None
        if user_lat is not None and user_lon is not None:
            user_point = func.ST_SetSRID(func.ST_MakePoint(user_lon, user_lat), 4326)
            # Distance in kilometers (ST_Distance on geography returns meters)
            dist_expr = func.ST_Distance(func.cast(Facility.geom, Geography), func.cast(user_point, Geography)) / 1000.0
            stmt = select(Facility, dist_expr.label("distance_km"))
            # Radius filter in meters
            stmt = stmt.where(
                func.ST_DWithin(func.cast(Facility.geom, Geography), func.cast(user_point, Geography), radius_km * 1000.0)
            )

        # City / State filters
        if city:
            stmt = stmt.where(func.lower(Facility.city) == city.lower())
        if state:
            stmt = stmt.where(func.lower(Facility.state) == state.lower())

        # Facility type filter
        if facility_type:
            stmt = stmt.where(func.lower(Facility.facility_type) == facility_type.lower())

        # Verification status filter
        if verification_status:
            stmt = stmt.where(Facility.verification_status == verification_status.upper())

        # Query text match
        if query and query.strip():
            q_term = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Facility.name).ilike(q_term),
                    func.lower(Facility.locality).ilike(q_term),
                    func.lower(Facility.city).ilike(q_term),
                    func.lower(Facility.address_line1).ilike(q_term),
                )
            )

        res = await db.execute(stmt)
        cards: list[ProviderCard] = []

        if user_lat is not None and user_lon is not None:
            rows = res.all()
            for fac, d_km in rows:
                if open_now and not self._is_facility_open_now(fac.operating_hours):
                    continue
                cards.append(self._facility_to_card(fac, round(float(d_km), 2) if d_km is not None else None))
        else:
            facilities = res.scalars().all()
            for fac in facilities:
                if open_now and not self._is_facility_open_now(fac.operating_hours):
                    continue
                cards.append(self._facility_to_card(fac, None))

        return cards

    async def _search_doctors(
        self,
        db: AsyncSession,
        query: str | None = None,
        user_lat: float | None = None,
        user_lon: float | None = None,
        radius_km: float = 10.0,
        city: str | None = None,
        state: str | None = None,
        specialty: str | None = None,
        verification_status: str | None = None,
    ) -> list[ProviderCard]:
        """Queries doctors and computes distance through their primary affiliated facility."""
        # Join Doctor with primary affiliation and facility
        stmt = (
            select(Doctor, Facility, DoctorAffiliation)
            .join(DoctorAffiliation, DoctorAffiliation.doctor_id == Doctor.id, isouter=True)
            .join(Facility, Facility.id == DoctorAffiliation.facility_id, isouter=True)
            .where(or_(DoctorAffiliation.is_primary.is_(True), DoctorAffiliation.id.is_(None)))
        )

        dist_expr = None
        if user_lat is not None and user_lon is not None:
            user_point = func.ST_SetSRID(func.ST_MakePoint(user_lon, user_lat), 4326)
            dist_expr = func.ST_Distance(func.cast(Facility.geom, Geography), func.cast(user_point, Geography)) / 1000.0
            stmt = select(Doctor, Facility, DoctorAffiliation, dist_expr.label("distance_km")).select_from(
                Doctor
            ).join(
                DoctorAffiliation, DoctorAffiliation.doctor_id == Doctor.id, isouter=True
            ).join(
                Facility, Facility.id == DoctorAffiliation.facility_id, isouter=True
            ).where(
                or_(DoctorAffiliation.is_primary.is_(True), DoctorAffiliation.id.is_(None))
            )
            # Filter within radius if primary facility has location
            stmt = stmt.where(
                or_(
                    func.ST_DWithin(func.cast(Facility.geom, Geography), func.cast(user_point, Geography), radius_km * 1000.0),
                    Facility.geom.is_(None),
                )
            )

        # Filters
        if city:
            stmt = stmt.where(func.lower(Facility.city) == city.lower())
        if state:
            stmt = stmt.where(func.lower(Facility.state) == state.lower())
        if verification_status:
            stmt = stmt.where(Doctor.verification_status == verification_status.upper())

        if specialty:
            spec_term = f"%{specialty.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Doctor.primary_specialty).ilike(spec_term),
                    func.cast(Doctor.secondary_specialties, String).ilike(spec_term),
                )
            )

        if query and query.strip():
            q_term = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Doctor.full_name).ilike(q_term),
                    func.lower(Doctor.primary_specialty).ilike(q_term),
                    func.lower(Doctor.qualifications).ilike(q_term),
                    func.lower(Facility.name).ilike(q_term),
                    func.lower(Facility.locality).ilike(q_term),
                    func.lower(Facility.city).ilike(q_term),
                )
            )

        res = await db.execute(stmt)
        cards: list[ProviderCard] = []

        if user_lat is not None and user_lon is not None:
            rows = res.all()
            for doc, fac, aff, d_km in rows:
                cards.append(self._doctor_to_card(doc, fac, aff, round(float(d_km), 2) if d_km is not None else None))
        else:
            rows = res.all()
            for doc, fac, aff in rows:
                cards.append(self._doctor_to_card(doc, fac, aff, None))

        return cards

    def _facility_to_card(self, fac: Facility, dist_km: float | None) -> ProviderCard:
        badge = self.build_verification_badge(
            status=fac.verification_status,
            tier=fac.verification_tier,
            source=fac.verification_source,
            method=fac.verification_method,
            verified_at=fac.verified_at,
            is_demo=fac.is_demo_data,
        )
        locality_str = f", {fac.locality}" if fac.locality else ""
        return ProviderCard(
            card_type="facility",
            id=fac.id,
            title=fac.name,
            subtitle=f"{fac.facility_type.replace('_', ' ').title()} in {fac.city}",
            facility_name=fac.name,
            facility_type=fac.facility_type,
            specialty=None,
            qualifications=None,
            experience_years=None,
            address_line=f"{fac.address_line1}{locality_str}, {fac.city}, {fac.state} - {fac.pincode}",
            city=fac.city,
            state=fac.state,
            latitude=fac.latitude,
            longitude=fac.longitude,
            distance_km=dist_km,
            phone=fac.phone or fac.emergency_phone,
            emergency_services_available=fac.emergency_services_available,
            languages_spoken=[],
            operating_hours=fac.operating_hours,
            verification=badge,
            is_demo_data=fac.is_demo_data,
        )

    def _doctor_to_card(
        self,
        doc: Doctor,
        fac: Facility | None,
        aff: DoctorAffiliation | None,
        dist_km: float | None,
    ) -> ProviderCard:
        badge = self.build_verification_badge(
            status=doc.verification_status,
            tier=doc.verification_tier,
            source=doc.verification_source,
            method=doc.verification_method,
            verified_at=doc.verified_at,
            is_demo=doc.is_demo_data,
        )
        address_line = "Primary location not specified"
        city = "Unknown"
        state = "Unknown"
        lat = 0.0
        lon = 0.0
        if fac:
            locality_str = f", {fac.locality}" if fac.locality else ""
            address_line = f"{fac.name}, {fac.address_line1}{locality_str}, {fac.city}"
            city = fac.city
            state = fac.state
            lat = fac.latitude
            lon = fac.longitude

        role = aff.role_or_designation if aff and aff.role_or_designation else "Consultant"
        subtitle = f"{doc.primary_specialty} • {role}"
        if fac:
            subtitle += f" at {fac.name}"

        return ProviderCard(
            card_type="doctor",
            id=doc.id,
            title=doc.full_name,
            subtitle=subtitle,
            facility_name=fac.name if fac else None,
            facility_type=fac.facility_type if fac else None,
            specialty=doc.primary_specialty,
            qualifications=doc.qualifications,
            experience_years=doc.experience_years,
            address_line=address_line,
            city=city,
            state=state,
            latitude=lat,
            longitude=lon,
            distance_km=dist_km,
            phone=fac.phone if fac else None,
            emergency_services_available=fac.emergency_services_available if fac else False,
            languages_spoken=doc.languages_spoken or [],
            operating_hours=aff.schedule if aff else None,
            verification=badge,
            is_demo_data=doc.is_demo_data,
        )

    @staticmethod
    def _is_facility_open_now(operating_hours: dict[str, Any] | None) -> bool:
        """Evaluates whether operating_hours indicate open status at current local time."""
        if not operating_hours:
            return True  # If not specified, do not filter out

        # Current weekday in lowercase (monday, tuesday, etc.)
        now = datetime.now(UTC)
        day_name = now.strftime("%A").lower()
        hours_str = operating_hours.get(day_name)
        if not hours_str or "closed" in hours_str.lower():
            return False
        if "00:00-23:59" in hours_str:
            return True

        # Parse simple HH:MM-HH:MM intervals
        current_minute = now.hour * 60 + now.minute
        for part in hours_str.split(","):
            part = part.strip()
            if "-" in part:
                try:
                    start_s, end_s = part.split("-")
                    sh, sm = map(int, start_s.strip().split(":"))
                    eh, em = map(int, end_s.strip().split(":"))
                    if (sh * 60 + sm) <= current_minute <= (eh * 60 + em):
                        return True
                except (ValueError, TypeError):
                    continue
        return False

    async def get_facility_details(self, db: AsyncSession, facility_id: UUID) -> FacilityDetail | None:
        """Retrieves comprehensive facility details including affiliated physicians."""
        stmt = (
            select(Facility)
            .where(Facility.id == facility_id)
            .options(
                selectinload(Facility.doctor_affiliations).selectinload(DoctorAffiliation.doctor)
            )
        )
        res = await db.execute(stmt)
        fac = res.scalars().first()
        if not fac:
            return None

        badge = self.build_verification_badge(
            status=fac.verification_status,
            tier=fac.verification_tier,
            source=fac.verification_source,
            method=fac.verification_method,
            verified_at=fac.verified_at,
            is_demo=fac.is_demo_data,
        )

        affiliated_docs: list[DoctorSummary] = []
        for aff in fac.doctor_affiliations:
            if aff.is_active and aff.doctor:
                doc = aff.doctor
                doc_badge = self.build_verification_badge(
                    status=doc.verification_status,
                    tier=doc.verification_tier,
                    source=doc.verification_source,
                    method=doc.verification_method,
                    verified_at=doc.verified_at,
                    is_demo=doc.is_demo_data,
                )
                affiliated_docs.append(
                    DoctorSummary(
                        id=doc.id,
                        full_name=doc.full_name,
                        qualifications=doc.qualifications,
                        primary_specialty=doc.primary_specialty,
                        experience_years=doc.experience_years,
                        languages_spoken=doc.languages_spoken or [],
                        consultation_fee=doc.consultation_fee,
                        primary_facility_id=fac.id,
                        primary_facility_name=fac.name,
                        facility_type=fac.facility_type,
                        city=fac.city,
                        state=fac.state,
                        latitude=fac.latitude,
                        longitude=fac.longitude,
                        verification=doc_badge,
                    )
                )

        return FacilityDetail(
            id=fac.id,
            name=fac.name,
            facility_type=fac.facility_type,
            address=AddressInfo(
                address_line1=fac.address_line1,
                address_line2=fac.address_line2,
                locality=fac.locality,
                city=fac.city,
                state=fac.state,
                pincode=fac.pincode,
                country=fac.country,
            ),
            location=LocationCoordinates(
                latitude=fac.latitude,
                longitude=fac.longitude,
            ),
            phone=fac.phone,
            emergency_phone=fac.emergency_phone,
            email=fac.email,
            website=fac.website,
            operating_hours=fac.operating_hours,
            emergency_services_available=fac.emergency_services_available,
            verification=badge,
            source_name=fac.source_name,
            source_url=fac.source_url,
            affiliated_doctors=affiliated_docs,
            created_at=fac.created_at,
            updated_at=fac.updated_at,
        )

    async def get_doctor_details(self, db: AsyncSession, doctor_id: UUID) -> DoctorDetail | None:
        """Retrieves comprehensive physician profile with affiliations and licensing metadata."""
        stmt = (
            select(Doctor)
            .where(Doctor.id == doctor_id)
            .options(
                selectinload(Doctor.affiliations).selectinload(DoctorAffiliation.facility)
            )
        )
        res = await db.execute(stmt)
        doc = res.scalars().first()
        if not doc:
            return None

        badge = self.build_verification_badge(
            status=doc.verification_status,
            tier=doc.verification_tier,
            source=doc.verification_source,
            method=doc.verification_method,
            verified_at=doc.verified_at,
            is_demo=doc.is_demo_data,
        )

        affiliations_data: list[dict[str, Any]] = []
        for aff in doc.affiliations:
            if aff.is_active and aff.facility:
                fac = aff.facility
                affiliations_data.append({
                    "facility_id": str(fac.id),
                    "facility_name": fac.name,
                    "facility_type": fac.facility_type,
                    "city": fac.city,
                    "locality": fac.locality,
                    "role_or_designation": aff.role_or_designation,
                    "schedule": aff.schedule,
                    "is_primary": aff.is_primary,
                    "phone": fac.phone,
                    "address": f"{fac.address_line1}, {fac.city}",
                })

        return DoctorDetail(
            id=doc.id,
            full_name=doc.full_name,
            gender=doc.gender,
            qualifications=doc.qualifications,
            primary_specialty=doc.primary_specialty,
            secondary_specialties=doc.secondary_specialties or [],
            registration_number=doc.registration_number,
            registration_council=doc.registration_council,
            experience_years=doc.experience_years,
            languages_spoken=doc.languages_spoken or [],
            consultation_fee=doc.consultation_fee,
            bio=doc.bio,
            verification=badge,
            source_name=doc.source_name,
            source_url=doc.source_url,
            affiliations=affiliations_data,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    async def get_specialties_summary(self, db: AsyncSession) -> SpecialtiesResponse:
        """Computes counts of providers by primary specialty."""
        stmt = (
            select(Doctor.primary_specialty, func.count(Doctor.id))
            .group_by(Doctor.primary_specialty)
            .order_by(func.count(Doctor.id).desc())
        )
        res = await db.execute(stmt)
        items = [SpecialtyItem(specialty=spec, count=cnt) for spec, cnt in res.all()]
        return SpecialtiesResponse(specialties=items)
