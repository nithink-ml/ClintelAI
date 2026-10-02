"""Provider Data Ingestion and Seeding Service."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.provider import (
    Doctor,
    DoctorAffiliation,
    Facility,
    VerificationStatus,
    VerificationTier,
)
from app.providers.schemas import IngestionStats


class ProviderSeeder:
    """Idempotently loads and synchronizes provider seed datasets into PostgreSQL PostGIS."""

    DEFAULT_SEED_FILE = Path(__file__).parent / "data" / "providers_seed.json"

    @classmethod
    async def seed(
        cls,
        db: AsyncSession,
        seed_path: Path | str | None = None,
        force_reload: bool = False,
    ) -> IngestionStats:
        """Parses and seeds facilities, doctors, and affiliations from JSON source."""
        file_path = Path(seed_path or cls.DEFAULT_SEED_FILE)
        if not file_path.exists():
            raise FileNotFoundError(f"Provider seed file not found at {file_path}")

        # Seed data is read during startup/admin sync
        with open(file_path, encoding="utf-8") as f:  # noqa: ASYNC230
            data: dict[str, Any] = json.load(f)

        raw_facilities = data.get("facilities", [])
        raw_doctors = data.get("doctors", [])

        facilities_ingested = 0
        doctors_ingested = 0
        affiliations_ingested = 0

        # Mapping of seed ID to database UUID
        facility_uuid_map: dict[str, UUID] = {}

        # 1. Ingest Facilities
        for fac_dict in raw_facilities:
            seed_id = fac_dict["id"]
            # Look up existing facility by name and city to ensure idempotency
            stmt = select(Facility).where(
                Facility.name == fac_dict["name"],
                Facility.city == fac_dict["city"],
            )
            res = await db.execute(stmt)
            existing_fac = res.scalars().first()

            verified_at = None
            if fac_dict.get("verified_at"):
                verified_at = datetime.fromisoformat(fac_dict["verified_at"])

            lat = float(fac_dict["latitude"])
            lon = float(fac_dict["longitude"])
            wkt_geom = WKTElement(f"POINT({lon} {lat})", srid=4326)

            if existing_fac:
                facility_uuid_map[seed_id] = existing_fac.id
                if force_reload:
                    existing_fac.facility_type = fac_dict["facility_type"]
                    existing_fac.address_line1 = fac_dict["address_line1"]
                    existing_fac.address_line2 = fac_dict.get("address_line2")
                    existing_fac.locality = fac_dict.get("locality")
                    existing_fac.state = fac_dict["state"]
                    existing_fac.pincode = fac_dict["pincode"]
                    existing_fac.latitude = lat
                    existing_fac.longitude = lon
                    existing_fac.geom = wkt_geom
                    existing_fac.phone = fac_dict.get("phone")
                    existing_fac.emergency_phone = fac_dict.get("emergency_phone")
                    existing_fac.email = fac_dict.get("email")
                    existing_fac.website = fac_dict.get("website")
                    existing_fac.operating_hours = fac_dict.get("operating_hours")
                    existing_fac.emergency_services_available = fac_dict.get("emergency_services_available", False)
                    existing_fac.verification_status = fac_dict.get("verification_status", VerificationStatus.DEMO_SIMULATED.value)
                    existing_fac.verification_tier = fac_dict.get("verification_tier", VerificationTier.TIER_4_DEMO.value)
                    existing_fac.verification_source = fac_dict.get("verification_source")
                    existing_fac.verification_method = fac_dict.get("verification_method")
                    existing_fac.verified_at = verified_at
                    existing_fac.is_demo_data = fac_dict.get("is_demo_data", True)
                    existing_fac.source_name = fac_dict.get("source_name", "ClintelAI Internal Dataset")
                    existing_fac.source_url = fac_dict.get("source_url")
            else:
                new_fac = Facility(
                    name=fac_dict["name"],
                    facility_type=fac_dict["facility_type"],
                    address_line1=fac_dict["address_line1"],
                    address_line2=fac_dict.get("address_line2"),
                    locality=fac_dict.get("locality"),
                    city=fac_dict["city"],
                    state=fac_dict["state"],
                    pincode=fac_dict["pincode"],
                    country=fac_dict.get("country", "India"),
                    latitude=lat,
                    longitude=lon,
                    geom=wkt_geom,
                    phone=fac_dict.get("phone"),
                    emergency_phone=fac_dict.get("emergency_phone"),
                    email=fac_dict.get("email"),
                    website=fac_dict.get("website"),
                    operating_hours=fac_dict.get("operating_hours"),
                    emergency_services_available=fac_dict.get("emergency_services_available", False),
                    verification_status=fac_dict.get("verification_status", VerificationStatus.DEMO_SIMULATED.value),
                    verification_tier=fac_dict.get("verification_tier", VerificationTier.TIER_4_DEMO.value),
                    verification_source=fac_dict.get("verification_source"),
                    verification_method=fac_dict.get("verification_method"),
                    verified_at=verified_at,
                    is_demo_data=fac_dict.get("is_demo_data", True),
                    source_name=fac_dict.get("source_name", "ClintelAI Internal Dataset"),
                    source_url=fac_dict.get("source_url"),
                )
                db.add(new_fac)
                await db.flush()
                facility_uuid_map[seed_id] = new_fac.id
                facilities_ingested += 1

        # 2. Ingest Doctors & Affiliations
        for doc_dict in raw_doctors:
            reg_num = doc_dict.get("registration_number")
            # Look up doctor by registration number or full name
            if reg_num:
                stmt = select(Doctor).where(Doctor.registration_number == reg_num)
            else:
                stmt = select(Doctor).where(Doctor.full_name == doc_dict["full_name"])
            res = await db.execute(stmt)
            existing_doc = res.scalars().first()

            verified_at = None
            if doc_dict.get("verified_at"):
                verified_at = datetime.fromisoformat(doc_dict["verified_at"])

            doc_id: UUID
            if existing_doc:
                doc_id = existing_doc.id
                if force_reload:
                    existing_doc.full_name = doc_dict["full_name"]
                    existing_doc.gender = doc_dict.get("gender")
                    existing_doc.qualifications = doc_dict["qualifications"]
                    existing_doc.primary_specialty = doc_dict["primary_specialty"]
                    existing_doc.secondary_specialties = doc_dict.get("secondary_specialties")
                    existing_doc.registration_number = reg_num
                    existing_doc.registration_council = doc_dict.get("registration_council")
                    existing_doc.experience_years = doc_dict.get("experience_years")
                    existing_doc.languages_spoken = doc_dict.get("languages_spoken")
                    existing_doc.consultation_fee = doc_dict.get("consultation_fee")
                    existing_doc.bio = doc_dict.get("bio")
                    existing_doc.verification_status = doc_dict.get("verification_status", VerificationStatus.DEMO_SIMULATED.value)
                    existing_doc.verification_tier = doc_dict.get("verification_tier", VerificationTier.TIER_4_DEMO.value)
                    existing_doc.verification_source = doc_dict.get("verification_source")
                    existing_doc.verification_method = doc_dict.get("verification_method")
                    existing_doc.verified_at = verified_at
                    existing_doc.is_demo_data = doc_dict.get("is_demo_data", True)
                    existing_doc.source_name = doc_dict.get("source_name", "ClintelAI Internal Dataset")
                    existing_doc.source_url = doc_dict.get("source_url")
            else:
                new_doc = Doctor(
                    full_name=doc_dict["full_name"],
                    gender=doc_dict.get("gender"),
                    qualifications=doc_dict["qualifications"],
                    primary_specialty=doc_dict["primary_specialty"],
                    secondary_specialties=doc_dict.get("secondary_specialties"),
                    registration_number=reg_num,
                    registration_council=doc_dict.get("registration_council"),
                    experience_years=doc_dict.get("experience_years"),
                    languages_spoken=doc_dict.get("languages_spoken"),
                    consultation_fee=doc_dict.get("consultation_fee"),
                    bio=doc_dict.get("bio"),
                    verification_status=doc_dict.get("verification_status", VerificationStatus.DEMO_SIMULATED.value),
                    verification_tier=doc_dict.get("verification_tier", VerificationTier.TIER_4_DEMO.value),
                    verification_source=doc_dict.get("verification_source"),
                    verification_method=doc_dict.get("verification_method"),
                    verified_at=verified_at,
                    is_demo_data=doc_dict.get("is_demo_data", True),
                    source_name=doc_dict.get("source_name", "ClintelAI Internal Dataset"),
                    source_url=doc_dict.get("source_url"),
                )
                db.add(new_doc)
                await db.flush()
                doc_id = new_doc.id
                doctors_ingested += 1

            # Affiliation
            primary_fac_seed_id = doc_dict.get("primary_facility_id")
            if primary_fac_seed_id and primary_fac_seed_id in facility_uuid_map:
                fac_uuid = facility_uuid_map[primary_fac_seed_id]
                aff_stmt = select(DoctorAffiliation).where(
                    DoctorAffiliation.doctor_id == doc_id,
                    DoctorAffiliation.facility_id == fac_uuid,
                )
                aff_res = await db.execute(aff_stmt)
                existing_aff = aff_res.scalars().first()
                if not existing_aff:
                    new_aff = DoctorAffiliation(
                        doctor_id=doc_id,
                        facility_id=fac_uuid,
                        role_or_designation=doc_dict.get("role_or_designation", "Attending Physician"),
                        schedule=doc_dict.get("schedule"),
                        is_primary=True,
                        is_active=True,
                    )
                    db.add(new_aff)
                    affiliations_ingested += 1

        await db.commit()
        logger.info(
            f"Provider seeding complete: {facilities_ingested} facilities, "
            f"{doctors_ingested} doctors, {affiliations_ingested} affiliations."
        )

        return IngestionStats(
            status="SUCCESS",
            facilities_ingested=facilities_ingested,
            doctors_ingested=doctors_ingested,
            affiliations_ingested=affiliations_ingested,
            is_demo_data=True,
            message="Successfully synchronized provider knowledge base.",
        )


if __name__ == "__main__":
    import asyncio

    async def main():
        async with AsyncSessionLocal() as session:
            stats = await ProviderSeeder.seed(session, force_reload=True)
            print(f"Provider Seeding Result: {stats}")

    asyncio.run(main())
