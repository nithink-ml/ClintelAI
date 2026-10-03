"""Regional Health Alerts Service: Geospatial matching, trusted source verification,
freshness evaluation, multilingual translation delivery, and clinical safety boundaries.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from geoalchemy2 import Geography
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.schemas import (
    FreshnessStatus,
    HealthAlertCreateRequest,
    HealthAlertDetail,
    HealthAlertSearchResponse,
    HealthAlertSummary,
    HealthAlertUpdateRequest,
)
from app.models.alert import AlertSeverity, AlertStatus, HealthAlert
from app.providers.geocoding import CompositeGeoProvider
from app.rag.safety import MedicalSafetyEngine


class HealthAlertService:
    """Orchestrates trusted health alert querying, geospatial boundaries, and administrative ingestion."""

    # Accredited public health institutions and regulatory authorities
    TRUSTED_AUTHORITY_PATTERNS = [
        "ministry of health",
        "mohfw",
        "national centre for disease control",
        "ncdc",
        "world health organization",
        "who",
        "indian council of medical research",
        "icmr",
        "directorate of public health",
        "directorate of health services",
        "department of health",
        "public health department",
        "central pollution control board",
        "cpcb",
        "india meteorological department",
        "imd",
        "integrated disease surveillance programme",
        "idsp",
        "state health mission",
        "dghs",
    ]

    TRUSTED_DOMAIN_PATTERNS = [
        ".gov.in",
        ".nic.in",
        ".who.int",
        ".icmr.org.in",
        ".nih.gov",
        "karnataka.gov.in",
        "dph.tn.gov.in",
        "dhs.kerala.gov.in",
        "cpcb.nic.in",
        "ncdc.gov.in",
        "mohfw.gov.in",
    ]

    UNVERIFIED_SOURCE_TERMS = [
        "twitter.com",
        "x.com",
        "facebook.com",
        "instagram.com",
        "reddit.com",
        "t.me",
        "telegram",
        "whatsapp",
        "tiktok",
        "blogspot",
        "wordpress",
        "unverified community",
        "rumor",
        "social media",
    ]

    def __init__(self, geo_provider: CompositeGeoProvider | None = None):
        self.geocoder = geo_provider or CompositeGeoProvider(allow_network=False)

    @classmethod
    def validate_trusted_source(cls, source_name: str, source_url: str) -> None:
        """Enforces trusted-source-only constraint. Rejects social media, blogs, or unverified claims."""
        s_name_lower = source_name.lower().strip()
        s_url_lower = source_url.lower().strip()

        # 1. Reject explicit unverified and social media platforms
        for unv in cls.UNVERIFIED_SOURCE_TERMS:
            if unv in s_url_lower or unv in s_name_lower:
                raise ValueError(
                    f"Health alerts cannot originate from unverified sources, social media, or blogs ('{unv}'). "
                    "Sources must strictly be accredited government health ministries, statutory bodies, or the WHO."
                )

        # 2. Check for recognized public health authority
        has_authority = any(auth in s_name_lower for auth in cls.TRUSTED_AUTHORITY_PATTERNS)
        has_gov_domain = any(dom in s_url_lower for dom in cls.TRUSTED_DOMAIN_PATTERNS)

        if not (has_authority or has_gov_domain):
            raise ValueError(
                f"Source '{source_name}' does not meet accredited public health authority standards. "
                "Accepted sources: MoHFW, NCDC, WHO, ICMR, State Health Directorates, or CPCB/IMD."
            )

    @staticmethod
    def compute_freshness(issued_at: datetime, valid_until: datetime | None) -> FreshnessStatus:
        """Evaluates temporal freshness and provides actionable verification instructions."""
        now = datetime.now(UTC)

        # Ensure tz-awareness
        if issued_at.tzinfo is None:
            issued_at = issued_at.replace(tzinfo=UTC)
        if valid_until and valid_until.tzinfo is None:
            valid_until = valid_until.replace(tzinfo=UTC)

        age_hours = max(0.0, (now - issued_at).total_seconds() / 3600.0)

        if valid_until and now > valid_until:
            return FreshnessStatus(
                status="EXPIRED",
                age_hours=round(age_hours, 1),
                last_verified_at=now,
                notice="This public health advisory is past its scheduled validity date. Check the official source for updates.",
            )
        elif age_hours <= 24.0:
            return FreshnessStatus(
                status="FRESH",
                age_hours=round(age_hours, 1),
                last_verified_at=now,
                notice="Fresh public health bulletin published within the last 24 hours.",
            )
        elif age_hours <= 168.0:  # 7 days
            return FreshnessStatus(
                status="RECENT",
                age_hours=round(age_hours, 1),
                last_verified_at=now,
                notice="Active health advisory published within the past 7 days.",
            )
        else:
            return FreshnessStatus(
                status="STALE",
                age_hours=round(age_hours, 1),
                last_verified_at=now,
                notice="Advisory was issued more than 7 days ago. Verify current active measures with primary source.",
            )

    @classmethod
    def apply_localization(
        cls,
        alert: HealthAlert,
        language: str,
    ) -> tuple[str, str, str, list[str]]:
        """Extracts localized text for title, summary, content, and precautionary measures."""
        lang_code = language.lower().strip()
        title = alert.title
        summary = alert.summary
        content = alert.content
        prec = alert.precautionary_measures or []

        if lang_code != "en" and alert.translations and lang_code in alert.translations:
            trans = alert.translations[lang_code]
            if isinstance(trans, dict):
                title = trans.get("title", title)
                summary = trans.get("summary", summary)
                content = trans.get("content", content)
                prec = trans.get("precautionary_measures", prec)

        return title, summary, content, prec

    async def search_alerts(
        self,
        db: AsyncSession,
        query: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        state: str | None = None,
        district: str | None = None,
        city: str | None = None,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = "ACTIVE",
        language: str = "en",
        page: int = 1,
        page_size: int = 10,
    ) -> HealthAlertSearchResponse:
        """Executes regional, category, severity, and text search over verified public health alerts."""
        applied_filters: dict[str, Any] = {
            "query": query,
            "lat": lat,
            "lon": lon,
            "state": state,
            "district": district,
            "city": city,
            "category": category,
            "severity": severity,
            "status": status,
            "language": language,
        }

        # 1. Clinical Emergency Red-Flag Interception (Phase 2 Safety Boundary)
        emergency_escalation = None
        if query and query.strip():
            escalation = MedicalSafetyEngine.evaluate_emergency(query.strip(), language=language)
            if escalation.is_emergency:
                emergency_escalation = escalation

        # 2. Build Base Query
        stmt = select(HealthAlert)

        # Status filtering
        if status:
            stmt = stmt.where(HealthAlert.status == status.upper())

        # Category filtering
        if category:
            stmt = stmt.where(func.lower(HealthAlert.category) == category.lower().strip())

        # Severity filtering
        if severity:
            stmt = stmt.where(HealthAlert.severity == severity.upper().strip())

        # 3. Regional and Geographic Matching
        # National alerts (state == 'ALL_INDIA' or state is NULL) ALWAYS match all queries
        national_cond = or_(
            HealthAlert.state.is_(None),
            func.upper(HealthAlert.state) == "ALL_INDIA",
        )

        user_point = None
        if lat is not None and lon is not None:
            user_point = func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326)
            # Distance computation in km
            dist_expr = func.ST_Distance(func.cast(HealthAlert.geom, Geography), func.cast(user_point, Geography)) / 1000.0

            # Match if:
            # a) within affected_radius_km of point
            # b) or point is within polygon
            # c) or national alert
            spatial_match = or_(
                national_cond,
                func.ST_DWithin(
                    func.cast(HealthAlert.geom, Geography),
                    func.cast(user_point, Geography),
                    func.coalesce(HealthAlert.affected_radius_km, 50.0) * 1000.0,
                ),
            )
            stmt = select(HealthAlert, dist_expr.label("distance_km")).where(spatial_match)
        else:
            # Textual state/district/city matching (national alerts always included when filtering by region)
            if state or district or city:
                region_conditions = [national_cond]
                if state:
                    region_conditions.append(func.lower(HealthAlert.state) == state.lower().strip())
                if district:
                    region_conditions.append(func.lower(HealthAlert.district) == district.lower().strip())
                if city:
                    region_conditions.append(func.lower(HealthAlert.city) == city.lower().strip())

                stmt = stmt.where(or_(*region_conditions))

        # 4. Text Query Filtering
        if query and query.strip():
            q_term = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(HealthAlert.title).ilike(q_term),
                    func.lower(HealthAlert.summary).ilike(q_term),
                    func.lower(HealthAlert.content).ilike(q_term),
                    func.lower(HealthAlert.category).ilike(q_term),
                    func.lower(HealthAlert.source_name).ilike(q_term),
                )
            )

        res = await db.execute(stmt)

        raw_items: list[tuple[HealthAlert, float | None]] = []
        if lat is not None and lon is not None:
            for alert, dist_km in res.all():
                raw_items.append((alert, round(float(dist_km), 2) if dist_km is not None else None))
        else:
            for alert in res.scalars().all():
                raw_items.append((alert, None))

        # 5. Sort items: Severity (CRITICAL > HIGH > MODERATE > LOW > INFORMATIONAL) then distance then issued_at DESC
        severity_rank = {
            AlertSeverity.CRITICAL.value: 1,
            AlertSeverity.HIGH.value: 2,
            AlertSeverity.MODERATE.value: 3,
            AlertSeverity.LOW.value: 4,
            AlertSeverity.INFORMATIONAL.value: 5,
        }

        def sort_key(item_tuple: tuple[HealthAlert, float | None]):
            al, d_km = item_tuple
            s_rank = severity_rank.get(al.severity, 6)
            d = d_km if d_km is not None else 9999.0
            t = al.issued_at.timestamp() if al.issued_at else 0
            return (s_rank, d, -t)

        raw_items.sort(key=sort_key)

        # 6. Pagination
        total = len(raw_items)
        page = max(1, page)
        page_size = max(1, min(50, page_size))
        total_pages = max(1, (total + page_size - 1) // page_size)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_items = raw_items[start_idx:end_idx]

        critical_active_count = sum(
            1 for al, _ in raw_items if al.status == AlertStatus.ACTIVE.value and al.severity == AlertSeverity.CRITICAL.value
        )

        # 7. Convert to Summaries with Freshness & Localization
        summaries: list[HealthAlertSummary] = []
        for alert, d_km in paged_items:
            loc_title, loc_summary, _, _ = self.apply_localization(alert, language)
            freshness = self.compute_freshness(alert.issued_at, alert.valid_until)

            summaries.append(
                HealthAlertSummary(
                    id=alert.id,
                    title=loc_title,
                    summary=loc_summary,
                    category=alert.category,
                    severity=alert.severity,
                    status=alert.status,
                    source_name=alert.source_name,
                    source_url=alert.source_url,
                    source_reference_id=alert.source_reference_id,
                    issued_at=alert.issued_at,
                    valid_from=alert.valid_from,
                    valid_until=alert.valid_until,
                    country=alert.country,
                    state=alert.state,
                    district=alert.district,
                    city=alert.city,
                    latitude=alert.latitude,
                    longitude=alert.longitude,
                    affected_radius_km=alert.affected_radius_km,
                    distance_km=d_km,
                    freshness=freshness,
                    is_demo_data=alert.is_demo_data,
                )
            )

        disclaimer = (
            "Notice: Regional health alerts provide official public health advisories from accredited government and global health agencies. "
            "They do not constitute individualized clinical diagnosis or personalized medical advice. "
            "If you are experiencing acute medical symptoms, consult a qualified physician or call national emergency services (112 / 108)."
        )

        return HealthAlertSearchResponse(
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            items=summaries,
            critical_active_count=critical_active_count,
            emergency_escalation=emergency_escalation,
            applied_filters=applied_filters,
            disclaimer=disclaimer,
        )

    async def get_alert_detail(
        self,
        db: AsyncSession,
        alert_id: UUID,
        language: str = "en",
    ) -> HealthAlertDetail | None:
        """Retrieves comprehensive public health advisory dossier with multilingual translation."""
        stmt = select(HealthAlert).where(HealthAlert.id == alert_id)
        res = await db.execute(stmt)
        alert = res.scalars().first()
        if not alert:
            return None

        loc_title, loc_summary, loc_content, loc_prec = self.apply_localization(alert, language)
        freshness = self.compute_freshness(alert.issued_at, alert.valid_until)

        return HealthAlertDetail(
            id=alert.id,
            title=loc_title,
            summary=loc_summary,
            content=loc_content,
            category=alert.category,
            severity=alert.severity,
            status=alert.status,
            source_name=alert.source_name,
            source_url=alert.source_url,
            source_reference_id=alert.source_reference_id,
            issued_at=alert.issued_at,
            valid_from=alert.valid_from,
            valid_until=alert.valid_until,
            country=alert.country,
            state=alert.state,
            district=alert.district,
            city=alert.city,
            locality=alert.locality,
            latitude=alert.latitude,
            longitude=alert.longitude,
            affected_radius_km=alert.affected_radius_km,
            symptoms=alert.symptoms or [],
            precautionary_measures=loc_prec,
            helpline_numbers=alert.helpline_numbers or [],
            translations=alert.translations,
            freshness=freshness,
            is_demo_data=alert.is_demo_data,
            provenance_audit=alert.provenance_audit,
            created_at=alert.created_at,
            updated_at=alert.updated_at,
        )

    async def create_alert(
        self,
        db: AsyncSession,
        req: HealthAlertCreateRequest,
    ) -> HealthAlertDetail:
        """Creates a new health alert following strict trusted source validation."""
        self.validate_trusted_source(req.source_name, req.source_url)

        # Set PostGIS geometry if coordinates provided
        geom = None
        if req.latitude is not None and req.longitude is not None:
            geom = func.ST_SetSRID(func.ST_MakePoint(req.longitude, req.latitude), 4326)

        alert = HealthAlert(
            title=req.title,
            summary=req.summary,
            content=req.content,
            category=req.category,
            severity=req.severity,
            status=req.status,
            source_name=req.source_name,
            source_url=req.source_url,
            source_reference_id=req.source_reference_id,
            issued_at=req.issued_at,
            valid_from=req.valid_from,
            valid_until=req.valid_until,
            country=req.country,
            state=req.state,
            district=req.district,
            city=req.city,
            locality=req.locality,
            latitude=req.latitude,
            longitude=req.longitude,
            affected_radius_km=req.affected_radius_km,
            geom=geom,
            symptoms=req.symptoms,
            precautionary_measures=req.precautionary_measures,
            helpline_numbers=req.helpline_numbers,
            translations=req.translations,
            is_demo_data=req.is_demo_data,
            provenance_audit={
                "ingestion_timestamp": datetime.now(UTC).isoformat(),
                "created_via": "ADMIN_API_INGESTION",
            },
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        detail = await self.get_alert_detail(db, alert.id)
        if not detail:
            raise RuntimeError("Failed to retrieve created health alert")
        return detail

    async def update_alert(
        self,
        db: AsyncSession,
        alert_id: UUID,
        req: HealthAlertUpdateRequest,
    ) -> HealthAlertDetail | None:
        """Updates alert fields (status, validity, severity, translations)."""
        stmt = select(HealthAlert).where(HealthAlert.id == alert_id)
        res = await db.execute(stmt)
        alert = res.scalars().first()
        if not alert:
            return None

        if req.title is not None:
            alert.title = req.title
        if req.summary is not None:
            alert.summary = req.summary
        if req.content is not None:
            alert.content = req.content
        if req.category is not None:
            alert.category = req.category
        if req.severity is not None:
            alert.severity = req.severity
        if req.status is not None:
            alert.status = req.status
        if req.valid_until is not None:
            alert.valid_until = req.valid_until
        if req.precautionary_measures is not None:
            alert.precautionary_measures = req.precautionary_measures
        if req.helpline_numbers is not None:
            alert.helpline_numbers = req.helpline_numbers
        if req.translations is not None:
            alert.translations = req.translations

        await db.commit()
        await db.refresh(alert)
        return await self.get_alert_detail(db, alert.id)
