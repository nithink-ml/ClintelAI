"""create_health_alerts_tables

Revision ID: 7c8910d5e6f1
Revises: 5715e8c21ca8
Create Date: 2026-10-03 02:00:00.000000

"""
from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7c8910d5e6f1"
down_revision: str | Sequence[str] | None = "5715e8c21ca8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: Create PostGIS tables for health alerts and regional boundaries."""
    op.create_table(
        "health_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="public_health_advisory"),
        sa.Column("severity", sa.String(length=50), nullable=False, server_default="MODERATE"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("source_reference_id", sa.String(length=100), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("country", sa.String(length=50), nullable=False, server_default="India"),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("locality", sa.String(length=100), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("affected_radius_km", sa.Float(), nullable=True),
        sa.Column(
            "geom",
            geoalchemy2.types.Geometry(geometry_type="GEOMETRY", srid=4326, spatial_index=True),
            nullable=True,
        ),
        sa.Column("translations", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("symptoms", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("precautionary_measures", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("helpline_numbers", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("is_demo_data", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("provenance_audit", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Indexes for fast lookup and spatial queries
    op.create_index(op.f("ix_health_alerts_id"), "health_alerts", ["id"], unique=False)
    op.create_index(op.f("ix_health_alerts_title"), "health_alerts", ["title"], unique=False)
    op.create_index(op.f("ix_health_alerts_category"), "health_alerts", ["category"], unique=False)
    op.create_index(op.f("ix_health_alerts_severity"), "health_alerts", ["severity"], unique=False)
    op.create_index(op.f("ix_health_alerts_status"), "health_alerts", ["status"], unique=False)
    op.create_index(op.f("ix_health_alerts_source_name"), "health_alerts", ["source_name"], unique=False)
    op.create_index(op.f("ix_health_alerts_state"), "health_alerts", ["state"], unique=False)
    op.create_index(op.f("ix_health_alerts_district"), "health_alerts", ["district"], unique=False)
    op.create_index(op.f("ix_health_alerts_city"), "health_alerts", ["city"], unique=False)
    op.create_index(op.f("ix_health_alerts_is_demo_data"), "health_alerts", ["is_demo_data"], unique=False)


def downgrade() -> None:
    """Downgrade schema: Drop health alerts table."""
    op.drop_index(op.f("ix_health_alerts_is_demo_data"), table_name="health_alerts")
    op.drop_index(op.f("ix_health_alerts_city"), table_name="health_alerts")
    op.drop_index(op.f("ix_health_alerts_district"), table_name="health_alerts")
    op.drop_index(op.f("ix_health_alerts_state"), table_name="health_alerts")
    op.drop_index(op.f("ix_health_alerts_source_name"), table_name="health_alerts")
    op.drop_index(op.f("ix_health_alerts_status"), table_name="health_alerts")
    op.drop_index(op.f("ix_health_alerts_severity"), table_name="health_alerts")
    op.drop_index(op.f("ix_health_alerts_category"), table_name="health_alerts")
    op.drop_index(op.f("ix_health_alerts_title"), table_name="health_alerts")
    op.drop_index(op.f("ix_health_alerts_id"), table_name="health_alerts")
    op.drop_table("health_alerts")
