"""Health Alert Seeding Service for Canonical Authoritative Advisories."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.alert import HealthAlert


class HealthAlertSeeder:
    """Idempotently loads canonical public health alerts and bulletins into PostgreSQL PostGIS."""

    DEFAULT_SEED_FILE = Path(__file__).parent / "data" / "canonical_alerts.json"

    @classmethod
    async def seed(
        cls,
        db: AsyncSession,
        seed_path: Path | str | None = None,
        force_reload: bool = False,
    ) -> dict[str, int]:
        """Parses and seeds canonical health alerts from JSON source."""
        file_path = Path(seed_path or cls.DEFAULT_SEED_FILE)
        if not file_path.exists():
            raise FileNotFoundError(f"Alert seed file not found at {file_path}")

        # Seed data is read during startup/admin sync
        with open(file_path, encoding="utf-8") as f:  # noqa: ASYNC230
            raw_alerts: list[dict[str, Any]] = json.load(f)

        alerts_created = 0
        alerts_updated = 0

        for alert_dict in raw_alerts:
            alert_id = UUID(alert_dict["id"])
            stmt = select(HealthAlert).where(HealthAlert.id == alert_id)
            res = await db.execute(stmt)
            existing = res.scalars().first()

            issued_at = datetime.fromisoformat(alert_dict["issued_at"])
            valid_from = datetime.fromisoformat(alert_dict["valid_from"])
            valid_until = None
            if alert_dict.get("valid_until"):
                valid_until = datetime.fromisoformat(alert_dict["valid_until"])

            lat = alert_dict.get("latitude")
            lon = alert_dict.get("longitude")
            wkt_geom = None
            if lat is not None and lon is not None:
                wkt_geom = WKTElement(f"POINT({lon} {lat})", srid=4326)

            provenance = {
                "seeded_from": str(file_path.name),
                "source_authority": alert_dict["source_name"],
                "source_url": alert_dict["source_url"],
                "ingested_at": datetime.now(UTC).isoformat(),
            }

            if existing:
                if force_reload:
                    existing.title = alert_dict["title"]
                    existing.summary = alert_dict["summary"]
                    existing.content = alert_dict["content"]
                    existing.category = alert_dict["category"]
                    existing.severity = alert_dict["severity"]
                    existing.status = alert_dict["status"]
                    existing.source_name = alert_dict["source_name"]
                    existing.source_url = alert_dict["source_url"]
                    existing.source_reference_id = alert_dict.get("source_reference_id")
                    existing.issued_at = issued_at
                    existing.valid_from = valid_from
                    existing.valid_until = valid_until
                    existing.country = alert_dict.get("country", "India")
                    existing.state = alert_dict.get("state")
                    existing.district = alert_dict.get("district")
                    existing.city = alert_dict.get("city")
                    existing.locality = alert_dict.get("locality")
                    existing.latitude = lat
                    existing.longitude = lon
                    existing.affected_radius_km = alert_dict.get("affected_radius_km")
                    existing.geom = wkt_geom
                    existing.symptoms = alert_dict.get("symptoms", [])
                    existing.precautionary_measures = alert_dict.get("precautionary_measures", [])
                    existing.helpline_numbers = alert_dict.get("helpline_numbers", [])
                    existing.translations = alert_dict.get("translations", {})
                    existing.is_demo_data = alert_dict.get("is_demo_data", True)
                    existing.provenance_audit = provenance
                    alerts_updated += 1
            else:
                new_alert = HealthAlert(
                    id=alert_id,
                    title=alert_dict["title"],
                    summary=alert_dict["summary"],
                    content=alert_dict["content"],
                    category=alert_dict["category"],
                    severity=alert_dict["severity"],
                    status=alert_dict["status"],
                    source_name=alert_dict["source_name"],
                    source_url=alert_dict["source_url"],
                    source_reference_id=alert_dict.get("source_reference_id"),
                    issued_at=issued_at,
                    valid_from=valid_from,
                    valid_until=valid_until,
                    country=alert_dict.get("country", "India"),
                    state=alert_dict.get("state"),
                    district=alert_dict.get("district"),
                    city=alert_dict.get("city"),
                    locality=alert_dict.get("locality"),
                    latitude=lat,
                    longitude=lon,
                    affected_radius_km=alert_dict.get("affected_radius_km"),
                    geom=wkt_geom,
                    symptoms=alert_dict.get("symptoms", []),
                    precautionary_measures=alert_dict.get("precautionary_measures", []),
                    helpline_numbers=alert_dict.get("helpline_numbers", []),
                    translations=alert_dict.get("translations", {}),
                    is_demo_data=alert_dict.get("is_demo_data", True),
                    provenance_audit=provenance,
                )
                db.add(new_alert)
                alerts_created += 1

        await db.commit()
        logger.info(
            f"HealthAlertSeeder completed: created {alerts_created}, updated {alerts_updated} health alerts."
        )
        return {"created": alerts_created, "updated": alerts_updated}
