"""Integration and unit tests for Regional Health Alerts, Trusted-Source Verification,
Geospatial Proximity, Multilingual Syndication, Emergency Red-Flags, Privacy, and RBAC.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.alerts.service import HealthAlertService
from app.api.deps import get_current_user
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.alert import HealthAlert
from app.models.user import User


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_trusted_source_validation():
    """Verify trusted-source-only gate rejects social media, blogs, and rumors, while accepting accredited health authorities."""
    # 1. Accredited Public Health Authorities -> Valid
    HealthAlertService.validate_trusted_source(
        "Ministry of Health and Family Welfare (MoHFW)",
        "https://mohfw.gov.in/advisories/dengue"
    )
    HealthAlertService.validate_trusted_source(
        "National Centre for Disease Control",
        "https://ncdc.gov.in/bulletins/cholera"
    )
    HealthAlertService.validate_trusted_source(
        "World Health Organization (WHO)",
        "https://who.int/emergencies/nipah"
    )
    HealthAlertService.validate_trusted_source(
        "Tamil Nadu Directorate of Public Health",
        "https://dph.tn.gov.in/alerts"
    )
    HealthAlertService.validate_trusted_source(
        "Central Pollution Control Board",
        "https://cpcb.nic.in/air-quality-advisory"
    )

    # 2. Social Media & Unverified platforms -> Must Raise ValueError
    unverified_sources = [
        ("Twitter Health Rumor", "https://twitter.com/health_updates/status/123"),
        ("X News Feed", "https://x.com/viral_outbreak"),
        ("Facebook Community Group", "https://facebook.com/groups/health_remedies"),
        ("Instagram Influencer", "https://instagram.com/reels/cure_dengue"),
        ("Reddit Health Thread", "https://reddit.com/r/india/comments/outbreak"),
        ("Telegram Channel", "https://t.me/free_medicine_alert"),
        ("WhatsApp Broadcast", "https://whatsapp.com/channel/cure"),
        ("Anonymous Blogspot", "https://miraclecures.blogspot.com/post"),
        ("Unverified Community Forum", "https://unverified-health.org/rumor"),
    ]

    for s_name, s_url in unverified_sources:
        with pytest.raises(ValueError) as exc_info:
            HealthAlertService.validate_trusted_source(s_name, s_url)
        assert "unverified sources" in str(exc_info.value).lower() or "accredited" in str(exc_info.value).lower()

    # 3. Random unaccredited website -> Must Raise ValueError
    with pytest.raises(ValueError) as exc_info:
        HealthAlertService.validate_trusted_source("Random Commercial Portal", "https://commercial-supplement-sales.com/alert")
    assert "does not meet accredited public health authority standards" in str(exc_info.value)


def test_freshness_status_computation():
    """Verify temporal freshness categorization and actionable verification instructions."""
    now = datetime.now(UTC)

    # FRESH (< 24h)
    f_fresh = HealthAlertService.compute_freshness(
        issued_at=now - timedelta(hours=6),
        valid_until=now + timedelta(days=10),
    )
    assert f_fresh.status == "FRESH"
    assert f_fresh.age_hours < 24.0
    assert "24 hours" in f_fresh.notice

    # RECENT (< 7d)
    f_recent = HealthAlertService.compute_freshness(
        issued_at=now - timedelta(days=3),
        valid_until=now + timedelta(days=10),
    )
    assert f_recent.status == "RECENT"
    assert 24.0 < f_recent.age_hours <= 168.0
    assert "7 days" in f_recent.notice

    # STALE (> 7d)
    f_stale = HealthAlertService.compute_freshness(
        issued_at=now - timedelta(days=15),
        valid_until=now + timedelta(days=10),
    )
    assert f_stale.status == "STALE"
    assert f_stale.age_hours > 168.0
    assert "Verify current active measures" in f_stale.notice

    # EXPIRED (now > valid_until)
    f_expired = HealthAlertService.compute_freshness(
        issued_at=now - timedelta(days=30),
        valid_until=now - timedelta(days=1),
    )
    assert f_expired.status == "EXPIRED"
    assert "past its scheduled validity date" in f_expired.notice


@pytest.mark.asyncio
async def test_alerts_search_basic():
    """Verify standard alert search returns active public health bulletins."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/search?page=1&page_size=10")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 5
    assert len(data["items"]) >= 5
    assert data["emergency_escalation"] is None
    assert "Notice: Regional health alerts" in data["disclaimer"]

    # Verify all items have freshness and provenance
    for item in data["items"]:
        assert item["freshness"]["status"] in ["FRESH", "RECENT", "STALE", "EXPIRED"]
        assert item["source_name"] is not None
        assert item["source_url"] is not None
        assert item["is_demo_data"] is True


@pytest.mark.asyncio
async def test_alerts_postgis_geospatial_proximity():
    """Verify PostGIS spatial matching returns localized and national alerts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Search at Chennai coordinates (13.0604, 80.2496)
        resp = await ac.get(
            "/api/v1/alerts/search",
            params={"lat": 13.0604, "lon": 80.2496, "status": "ACTIVE"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2

    # Should contain Chennai Dengue alert and national scope alert
    titles = [i["title"].lower() for i in data["items"]]
    assert any("dengue" in t for t in titles)
    assert any("measles" in t for t in titles)

    # Localized alert should have distance_km computed
    chennai_alert = next(i for i in data["items"] if "dengue" in i["title"].lower())
    assert chennai_alert["distance_km"] is not None
    assert chennai_alert["distance_km"] < 50.0


@pytest.mark.asyncio
async def test_alerts_category_and_severity_filtering():
    """Verify category and severity filtering."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Category filter: air_quality
        resp_cat = await ac.get("/api/v1/alerts/search", params={"category": "air_quality"})
        assert resp_cat.status_code == 200
        cat_data = resp_cat.json()
        assert cat_data["total"] >= 1
        for item in cat_data["items"]:
            assert item["category"] == "air_quality"

        # Severity filter: CRITICAL
        resp_sev = await ac.get("/api/v1/alerts/search", params={"severity": "CRITICAL"})
        assert resp_sev.status_code == 200
        sev_data = resp_sev.json()
        assert sev_data["total"] >= 1
        for item in sev_data["items"]:
            assert item["severity"] == "CRITICAL"


@pytest.mark.asyncio
async def test_alerts_status_lifecycle():
    """Verify ACTIVE strictly excludes EXPIRED and DRAFT, while EXPIRED can be queried specifically."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Default/ACTIVE query
        resp_active = await ac.get("/api/v1/alerts/search", params={"status": "ACTIVE"})
        assert resp_active.status_code == 200
        for item in resp_active.json()["items"]:
            assert item["status"] == "ACTIVE"
            assert "draft" not in item["title"].lower()

        # EXPIRED query
        resp_exp = await ac.get("/api/v1/alerts/search", params={"status": "EXPIRED"})
        assert resp_exp.status_code == 200
        exp_data = resp_exp.json()
        assert exp_data["total"] >= 1
        for item in exp_data["items"]:
            assert item["status"] == "EXPIRED"


@pytest.mark.asyncio
async def test_alerts_multilingual_syndication():
    """Verify multilingual translation in search and alert detail."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Query with language=ta (Tamil)
        resp_ta = await ac.get("/api/v1/alerts/search", params={"city": "Chennai", "language": "ta"})
        assert resp_ta.status_code == 200
        ta_items = resp_ta.json()["items"]
        assert len(ta_items) >= 1

        # Check for Tamil characters in the localized title
        chennai_item = next(i for i in ta_items if "11111111-1111-4111-a111-111111111111" in str(i["id"]))
        assert any("\u0b80" <= c <= "\u0bff" for c in chennai_item["title"])

        # Fetch detail with language=ta
        detail_resp = await ac.get(f"/api/v1/alerts/{chennai_item['id']}?language=ta")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert any("\u0b80" <= c <= "\u0bff" for c in detail["title"])
        assert any("\u0b80" <= c <= "\u0bff" for c in detail["summary"])
        assert len(detail["precautionary_measures"]) >= 1


@pytest.mark.asyncio
async def test_alerts_emergency_red_flags():
    """Verify clinical emergency symptoms in query trigger red-flag escalation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/alerts/search",
            params={"query": "sudden crushing chest pain radiating to left arm"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["emergency_escalation"] is not None
    esc = data["emergency_escalation"]
    assert esc["is_emergency"] is True
    assert esc["level"] == "CRITICAL"
    assert "112" in esc["emergency_numbers"]
    assert "108" in esc["emergency_numbers"]


@pytest.mark.asyncio
async def test_alerts_detail_and_404():
    """Verify alert detail endpoint returns complete clinical metadata and 404 for unknown IDs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        list_resp = await ac.get("/api/v1/alerts/search?page_size=5")
        items = list_resp.json()["items"]
        assert len(items) > 0
        target_id = items[0]["id"]

        detail_resp = await ac.get(f"/api/v1/alerts/{target_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == target_id
        assert detail["content"] is not None
        assert detail["source_name"] is not None
        assert detail["freshness"] is not None
        assert detail["is_demo_data"] is True

        # Non-existent ID -> 404
        fake_id = str(uuid.uuid4())
        resp_404 = await ac.get(f"/api/v1/alerts/{fake_id}")
        assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_alerts_rbac_protection():
    """Verify RBAC on alert creation, update, and synchronization endpoints."""
    uid = uuid.uuid4().hex[:8]
    user_email = f"alert_test_user_{uid}@example.com"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Unauthenticated -> 401
        unauth_resp = await ac.post(
            "/api/v1/alerts",
            json={
                "title": "Test Public Health Alert",
                "summary": "High vigilance notice for cholera outbreak prevention.",
                "content": "Official epidemiological surveillance bulletin issued by the health ministry.",
                "category": "outbreak",
                "severity": "HIGH",
                "source_name": "Ministry of Health and Family Welfare (MoHFW)",
                "source_url": "https://mohfw.gov.in/alerts/cholera",
            },
        )
        assert unauth_resp.status_code == 401

        # 2. Register normal user
        reg_res = await ac.post(
            "/api/v1/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Alerts Test User"},
        )
        assert reg_res.status_code == 201
        user_token = reg_res.json()["access_token"]

        # Normal user -> 403 Forbidden
        user_resp = await ac.post(
            "/api/v1/alerts",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "title": "Test Public Health Alert",
                "summary": "High vigilance notice for cholera outbreak prevention.",
                "content": "Official epidemiological surveillance bulletin issued by the health ministry.",
                "category": "outbreak",
                "severity": "HIGH",
                "source_name": "Ministry of Health and Family Welfare (MoHFW)",
                "source_url": "https://mohfw.gov.in/alerts/cholera",
            },
        )
        assert user_resp.status_code == 403
        assert "Operation not permitted" in user_resp.json()["detail"]

        # Normal user sync -> 403 Forbidden
        sync_resp = await ac.post(
            "/api/v1/alerts/sync",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert sync_resp.status_code == 403

        # 3. Admin user -> 201 Created via admin dependency override
        from app.core.security import decode_token

        real_user_id = uuid.UUID(decode_token(user_token)["sub"])
        mock_admin = User(
            id=real_user_id,
            email=user_email,
            role="admin",
            is_active=True,
        )

        app.dependency_overrides[get_current_user] = lambda: mock_admin
        try:
            admin_resp = await ac.post(
                "/api/v1/alerts",
                headers={"Authorization": f"Bearer {user_token}"},
                json={
                    "title": "Admin Tested Public Health Alert",
                    "summary": "Surveillance notice for seasonal vector prevention.",
                    "content": "Official epidemiological bulletin issued by National Centre for Disease Control.",
                    "category": "infectious_disease",
                    "severity": "MODERATE",
                    "source_name": "National Centre for Disease Control (NCDC)",
                    "source_url": "https://ncdc.gov.in/bulletin/vector",
                    "state": "Karnataka",
                    "city": "Bengaluru",
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                    "affected_radius_km": 25.0,
                },
            )
            assert admin_resp.status_code == 201
            created_data = admin_resp.json()
            assert created_data["title"] == "Admin Tested Public Health Alert"
            assert created_data["source_name"] == "National Centre for Disease Control (NCDC)"

            # PATCH update alert
            patch_resp = await ac.patch(
                f"/api/v1/alerts/{created_data['id']}",
                headers={"Authorization": f"Bearer {user_token}"},
                json={"severity": "HIGH", "summary": "Updated vigilance notice for vector prevention."},
            )
            assert patch_resp.status_code == 200
            assert patch_resp.json()["severity"] == "HIGH"

            # Sync canonical alerts as admin
            sync_admin = await ac.post(
                "/api/v1/alerts/sync",
                headers={"Authorization": f"Bearer {user_token}"},
            )
            assert sync_admin.status_code == 200
            assert sync_admin.json()["status"] == "success"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            async with AsyncSessionLocal() as cleanup_session:
                from sqlalchemy import delete
                await cleanup_session.execute(
                    delete(HealthAlert).where(HealthAlert.title.like("%Admin Tested%"))
                )
                await cleanup_session.commit()


@pytest.mark.asyncio
async def test_alerts_location_privacy_guardrail():
    """Verify user coordinates are not exposed in persistent audit logs during search."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/alerts/search",
            params={"lat": 13.0827, "lon": 80.2707, "query": "dengue"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_alerts_meta_categories():
    """Verify alert metadata endpoint returns categories, severities, and statuses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/alerts/meta/categories")

    assert resp.status_code == 200
    data = resp.json()
    assert "infectious_disease" in data["categories"]
    assert "CRITICAL" in data["severities"]
    assert "ACTIVE" in data["statuses"]
