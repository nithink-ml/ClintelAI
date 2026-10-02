"""create_provider_discovery_and_verification_tables

Revision ID: 5715e8c21ca8
Revises: 65069711647b
Create Date: 2026-10-01 23:22:43.298341

"""
from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5715e8c21ca8"
down_revision: str | Sequence[str] | None = "65069711647b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: Create PostGIS tables for facilities, doctors, and affiliations."""
    # Ensure PostGIS extension is active
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 1. Create facilities table
    op.create_table(
        "facilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("facility_type", sa.String(length=50), nullable=False, server_default="clinic"),
        sa.Column("address_line1", sa.String(length=255), nullable=False),
        sa.Column("address_line2", sa.String(length=255), nullable=True),
        sa.Column("locality", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("pincode", sa.String(length=20), nullable=False),
        sa.Column("country", sa.String(length=50), nullable=False, server_default="India"),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326, spatial_index=True),
            nullable=True,
        ),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("emergency_phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("operating_hours", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("emergency_services_available", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="DEMO_SIMULATED"),
        sa.Column("verification_tier", sa.String(length=50), nullable=False, server_default="tier_4_demo"),
        sa.Column("verification_source", sa.String(length=255), nullable=True),
        sa.Column("verification_method", sa.String(length=100), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo_data", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_name", sa.String(length=255), nullable=False, server_default="ClintelAI Internal Dataset"),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_facilities_id", "facilities", ["id"], unique=False)
    op.create_index("ix_facilities_name", "facilities", ["name"], unique=False)
    op.create_index("ix_facilities_facility_type", "facilities", ["facility_type"], unique=False)
    op.create_index("ix_facilities_locality", "facilities", ["locality"], unique=False)
    op.create_index("ix_facilities_city", "facilities", ["city"], unique=False)
    op.create_index("ix_facilities_state", "facilities", ["state"], unique=False)
    op.create_index("ix_facilities_pincode", "facilities", ["pincode"], unique=False)
    op.create_index("ix_facilities_verification_status", "facilities", ["verification_status"], unique=False)
    op.create_index("ix_facilities_is_demo_data", "facilities", ["is_demo_data"], unique=False)

    # Automatically synchronize geom on insert/update if not populated
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_facility_geom()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.geom IS NULL AND NEW.longitude IS NOT NULL AND NEW.latitude IS NOT NULL THEN
                NEW.geom := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_sync_facility_geom
        BEFORE INSERT OR UPDATE ON facilities
        FOR EACH ROW
        EXECUTE FUNCTION sync_facility_geom();
    """)

    # 2. Create doctors table
    op.create_table(
        "doctors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("gender", sa.String(length=50), nullable=True),
        sa.Column("qualifications", sa.String(length=255), nullable=False),
        sa.Column("primary_specialty", sa.String(length=100), nullable=False),
        sa.Column("secondary_specialties", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("registration_number", sa.String(length=100), nullable=True),
        sa.Column("registration_council", sa.String(length=150), nullable=True),
        sa.Column("experience_years", sa.Integer(), nullable=True),
        sa.Column("languages_spoken", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("consultation_fee", sa.Float(), nullable=True),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("verification_status", sa.String(length=50), nullable=False, server_default="DEMO_SIMULATED"),
        sa.Column("verification_tier", sa.String(length=50), nullable=False, server_default="tier_4_demo"),
        sa.Column("verification_source", sa.String(length=255), nullable=True),
        sa.Column("verification_method", sa.String(length=100), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo_data", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_name", sa.String(length=255), nullable=False, server_default="ClintelAI Internal Dataset"),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_doctors_id", "doctors", ["id"], unique=False)
    op.create_index("ix_doctors_full_name", "doctors", ["full_name"], unique=False)
    op.create_index("ix_doctors_primary_specialty", "doctors", ["primary_specialty"], unique=False)
    op.create_index("ix_doctors_registration_number", "doctors", ["registration_number"], unique=True)
    op.create_index("ix_doctors_verification_status", "doctors", ["verification_status"], unique=False)
    op.create_index("ix_doctors_is_demo_data", "doctors", ["is_demo_data"], unique=False)

    # 3. Create doctor_affiliations table
    op.create_table(
        "doctor_affiliations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_or_designation", sa.String(length=150), nullable=True),
        sa.Column("schedule", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_doctor_affiliations_id", "doctor_affiliations", ["id"], unique=False)
    op.create_index("ix_doctor_affiliations_doctor_id", "doctor_affiliations", ["doctor_id"], unique=False)
    op.create_index("ix_doctor_affiliations_facility_id", "doctor_affiliations", ["facility_id"], unique=False)
    op.create_index("ix_doctor_affiliations_is_active", "doctor_affiliations", ["is_active"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_sync_facility_geom ON facilities;")
    op.execute("DROP FUNCTION IF EXISTS sync_facility_geom();")
    op.drop_table("doctor_affiliations")
    op.drop_table("doctors")
    op.drop_table("facilities")
