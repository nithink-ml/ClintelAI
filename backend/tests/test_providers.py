"""Integration and unit tests for Doctor, Clinic & Hospital Discovery, PostGIS queries,
Verification tiers, Provenance metadata, Red-flag Emergency routing, Geocoding, and RBAC.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.provider import VerificationStatus, VerificationTier
from app.providers.service import ProviderService


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_provider_search_basic():
    """Verify standard provider discovery returns seeded facilities and doctors."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/search?page=1&page_size=10")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 10
    assert len(data["items"]) == 10
    assert data["emergency_escalation"] is None
    assert "Notice: ClintelAI Provider Discovery" in data["disclaimer"]

    # Verify synthetic demo labeling is unambiguous
    first_item = data["items"][0]
    assert first_item["is_demo_data"] is True
    assert first_item["verification"]["is_demo_data"] is True
    assert "DEMO" in first_item["verification"]["label"]


@pytest.mark.asyncio
async def test_postgis_distance_sorting():
    """Verify PostGIS spatial distance calculations sort nearest providers first."""
    # Apollo Hospital Chennai coordinates: (13.0604, 80.2496)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/providers/search",
            params={"lat": 13.0604, "lon": 80.2496, "radius_km": 15.0, "page_size": 5},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    items = data["items"]

    # Ensure items are ordered by increasing distance
    distances = [item["distance_km"] for item in items if item["distance_km"] is not None]
    assert len(distances) >= 2
    assert distances == sorted(distances)
    # The closest facility should be Apollo Hospital at ~0.0 km
    assert distances[0] <= 0.1


@pytest.mark.asyncio
async def test_radius_filtering():
    """Verify PostGIS ST_DWithin strictly limits search results within radius."""
    chennai_lat, chennai_lon = 13.0604, 80.2496
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Search with 2km radius
        resp_2km = await ac.get(
            "/api/v1/providers/search",
            params={"lat": chennai_lat, "lon": chennai_lon, "radius_km": 2.0, "page_size": 20},
        )
        # Search with 25km radius
        resp_25km = await ac.get(
            "/api/v1/providers/search",
            params={"lat": chennai_lat, "lon": chennai_lon, "radius_km": 25.0, "page_size": 20},
        )

    assert resp_2km.status_code == 200
    assert resp_25km.status_code == 200

    data_2km = resp_2km.json()
    data_25km = resp_25km.json()

    # All returned providers within 2km must have distance_km <= 2.0
    for item in data_2km["items"]:
        assert item["distance_km"] is not None
        assert item["distance_km"] <= 2.01

    # 25km radius must capture more or equal providers than 2km radius
    assert data_25km["total"] >= data_2km["total"]


@pytest.mark.asyncio
async def test_specialty_filtering():
    """Verify filtering providers by medical specialty."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/search", params={"specialty": "Pediatrics"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0
    for item in data["items"]:
        if item["card_type"] == "doctor":
            assert item["specialty"] == "Pediatrics"


@pytest.mark.asyncio
async def test_provider_type_filtering():
    """Verify filtering by provider type (doctor vs hospital vs clinic)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp_docs = await ac.get("/api/v1/providers/search", params={"provider_type": "doctor"})
        resp_hosp = await ac.get("/api/v1/providers/search", params={"provider_type": "hospital"})

    assert resp_docs.status_code == 200
    assert resp_hosp.status_code == 200

    data_docs = resp_docs.json()
    for item in data_docs["items"]:
        assert item["card_type"] == "doctor"

    data_hosp = resp_hosp.json()
    for item in data_hosp["items"]:
        assert item["card_type"] == "facility"
        assert item["facility_type"] == "hospital"


@pytest.mark.asyncio
async def test_verification_tiers_and_provenance():
    """Verify explicit verification tiers and mandatory provenance metadata under demo guardrail."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/providers/search",
            params={"verification_status": "VERIFIED"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] > 0

    for item in data["items"]:
        v = item["verification"]
        # STRICT DEMO GUARDRAIL: Synthetic data effective status is strictly DEMO_SIMULATED
        assert v["status"] == VerificationStatus.DEMO_SIMULATED.value
        assert v["effective_status"] == VerificationStatus.DEMO_SIMULATED.value
        assert v["tier"] == VerificationTier.TIER_4_DEMO.value
        assert v["effective_tier"] == VerificationTier.TIER_4_DEMO.value
        assert v["label"] == "DEMO_SIMULATED"
        # Simulated target tracks the simulated tier for benchmark auditing
        assert v["simulated_target_status"] == VerificationStatus.VERIFIED.value
        assert v["simulated_target_tier"] == VerificationTier.TIER_1_VERIFIED.value
        # Check provenance retention
        assert v["source"] is not None and len(v["source"]) > 0
        assert v["method"] is not None and len(v["method"]) > 0
        assert v["verified_at"] is not None
        # All demo entries must have is_demo_data=True
        assert v["is_demo_data"] is True
        assert item["is_demo_data"] is True
        assert item["effective_status"] == "DEMO_SIMULATED"
        assert "Simulated demonstration record. Do not use for actual clinical appointments or emergency care." in v["description"]


@pytest.mark.asyncio
async def test_demo_guardrail_synthetic_providers_never_presented_as_verified():
    """STRICT GUARDRAIL TEST (Requirement 5):
    Proves synthetic demo providers can NEVER be presented as officially verified,
    partially verified, or unverified. Effective status MUST ALWAYS be DEMO_SIMULATED.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Test search endpoint across all types and pages
        search_resp = await ac.get("/api/v1/providers/search?page_size=50")
        assert search_resp.status_code == 200
        items = search_resp.json()["items"]
        assert len(items) > 0

        for item in items:
            if item["is_demo_data"]:
                # Must NEVER have effective status VERIFIED, PARTIALLY_VERIFIED, or UNVERIFIED
                assert item["effective_status"] == "DEMO_SIMULATED"
                assert item["effective_status"] not in ("VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED")

                v = item["verification"]
                assert v["is_demo_data"] is True
                assert v["effective_status"] == "DEMO_SIMULATED"
                assert v["status"] == "DEMO_SIMULATED"
                assert v["effective_tier"] == "tier_4_demo"
                assert v["tier"] == "tier_4_demo"
                assert v["label"] == "DEMO_SIMULATED"
                assert v["status"] not in ("VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED")
                assert v["effective_status"] not in ("VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED")
                assert "Simulated demonstration record. Do not use for actual clinical appointments or emergency care." in v["description"]

        # 2. Test Facility details endpoint
        fac_item = next(i for i in items if i["card_type"] == "facility")
        fac_resp = await ac.get(f"/api/v1/providers/facilities/{fac_item['id']}")
        assert fac_resp.status_code == 200
        fac_data = fac_resp.json()
        assert fac_data["is_demo_data"] is True
        assert fac_data["effective_status"] == "DEMO_SIMULATED"
        assert fac_data["verification"]["effective_status"] == "DEMO_SIMULATED"
        assert fac_data["verification"]["status"] == "DEMO_SIMULATED"
        assert fac_data["verification"]["status"] not in ("VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED")
        assert fac_data["verification"]["label"] == "DEMO_SIMULATED"

        # 3. Test Doctor details endpoint
        doc_item = next(i for i in items if i["card_type"] == "doctor")
        doc_resp = await ac.get(f"/api/v1/providers/doctors/{doc_item['id']}")
        assert doc_resp.status_code == 200
        doc_data = doc_resp.json()
        assert doc_data["is_demo_data"] is True
        assert doc_data["effective_status"] == "DEMO_SIMULATED"
        assert doc_data["verification"]["effective_status"] == "DEMO_SIMULATED"
        assert doc_data["verification"]["status"] == "DEMO_SIMULATED"
        assert doc_data["verification"]["status"] not in ("VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED")
        assert doc_data["verification"]["label"] == "DEMO_SIMULATED"

        # 4. Direct unit test of ProviderService.build_verification_badge
        # Even if a caller attempts to build a badge with status="VERIFIED" and tier="tier_1_verified",
        # if is_demo=True, the effective status and tier MUST be DEMO_SIMULATED / tier_4_demo.
        badge = ProviderService.build_verification_badge(
            status="VERIFIED",
            tier="tier_1_verified",
            source="Test Source",
            method="TEST_METHOD",
            is_demo=True,
        )
        assert badge.is_demo_data is True
        assert badge.effective_status == "DEMO_SIMULATED"
        assert badge.status == "DEMO_SIMULATED"
        assert badge.effective_tier == "tier_4_demo"
        assert badge.tier == "tier_4_demo"
        assert badge.label == "DEMO_SIMULATED"
        assert badge.status != "VERIFIED"
        assert badge.simulated_target_status == "VERIFIED"
        assert badge.simulated_target_tier == "tier_1_verified"
        assert "Simulated demonstration record. Do not use for actual clinical appointments or emergency care." in badge.description

        # 5. Proves real verification tiers REMAIN available for future authoritative provider ingestion (is_demo=False)
        real_badge = ProviderService.build_verification_badge(
            status="VERIFIED",
            tier="tier_1_verified",
            source="National Medical Commission Registry",
            method="OFFICIAL_REGISTRY_API",
            is_demo=False,
        )
        assert real_badge.is_demo_data is False
        assert real_badge.effective_status == "VERIFIED"
        assert real_badge.status == "VERIFIED"
        assert real_badge.tier == "tier_1_verified"
        assert real_badge.label == "Officially Verified"
        assert real_badge.simulated_target_status is None


@pytest.mark.asyncio
async def test_emergency_query_red_flag_detection():
    """Verify that provider search flags acute red-flag symptoms with immediate emergency escalation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/providers/search",
            params={"query": "severe crushing chest pain radiating to arm and shortness of breath"},
        )

    assert resp.status_code == 200
    data = resp.json()
    escalation = data["emergency_escalation"]
    assert escalation is not None
    assert escalation["is_emergency"] is True
    assert escalation["level"] == "CRITICAL"
    assert "112" in escalation["emergency_numbers"]
    assert "108" in escalation["emergency_numbers"]
    assert "IMMEDIATE EMERGENCY ACTION REQUIRED" in escalation["action_message"]


@pytest.mark.asyncio
async def test_invalid_coordinates_validation():
    """Verify geographic coordinate input validation rejects out-of-bounds latitudes/longitudes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Latitude > 90
        resp_lat = await ac.get("/api/v1/providers/search", params={"lat": 120.0, "lon": 80.0})
        assert resp_lat.status_code == 422

        # Longitude > 180
        resp_lon = await ac.get("/api/v1/providers/search", params={"lat": 13.0, "lon": 220.0})
        assert resp_lon.status_code == 422


@pytest.mark.asyncio
async def test_empty_search_results():
    """Verify handling of empty search results with graceful status 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get(
            "/api/v1/providers/search",
            params={"query": "NonExistentHospitalXYZ999Unknown"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_nearby_endpoint():
    """Verify dedicated /nearby endpoint requires coordinates and sorts by proximity."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Without lat/lon -> 422
        resp_missing = await ac.get("/api/v1/providers/nearby")
        assert resp_missing.status_code == 422

        # With lat/lon -> 200
        resp_ok = await ac.get(
            "/api/v1/providers/nearby",
            params={"lat": 13.0604, "lon": 80.2496, "radius_km": 10.0},
        )
        assert resp_ok.status_code == 200
        data = resp_ok.json()
        assert data["total"] > 0
        assert data["items"][0]["distance_km"] is not None


@pytest.mark.asyncio
async def test_specialties_summary_endpoint():
    """Verify /specialties endpoint aggregates medical specialties with counts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/providers/specialties")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["specialties"]) > 0
    specialty_names = [s["specialty"] for s in data["specialties"]]
    assert "Cardiology" in specialty_names
    assert "Pediatrics" in specialty_names
    for item in data["specialties"]:
        assert item["count"] >= 1


@pytest.mark.asyncio
async def test_facility_and_doctor_details():
    """Verify individual provider detail endpoints and 404 behavior."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Fetch search list to grab real IDs
        list_resp = await ac.get("/api/v1/providers/search?page_size=10")
        items = list_resp.json()["items"]

        fac_id = next(i["id"] for i in items if i["card_type"] == "facility")
        doc_id = next(i["id"] for i in items if i["card_type"] == "doctor")

        # Facility details
        fac_resp = await ac.get(f"/api/v1/providers/facilities/{fac_id}")
        assert fac_resp.status_code == 200
        fac_data = fac_resp.json()
        assert fac_data["id"] == fac_id
        assert fac_data["address"]["city"] is not None
        assert fac_data["source_name"] is not None
        assert fac_data["verification"]["source"] is not None

        # Doctor details
        doc_resp = await ac.get(f"/api/v1/providers/doctors/{doc_id}")
        assert doc_resp.status_code == 200
        doc_data = doc_resp.json()
        assert doc_data["id"] == doc_id
        assert doc_data["registration_number"] is not None
        assert len(doc_data["affiliations"]) >= 1

        # Non-existent 404 test
        fake_id = str(uuid.uuid4())
        fac_404 = await ac.get(f"/api/v1/providers/facilities/{fake_id}")
        assert fac_404.status_code == 404

        doc_404 = await ac.get(f"/api/v1/providers/doctors/{fake_id}")
        assert doc_404.status_code == 404


@pytest.mark.asyncio
async def test_geocoding_and_fallback():
    """Verify local cache geocoding and graceful 404 fallback for unknown places."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Known city
        resp_chennai = await ac.get("/api/v1/providers/geocode?query=Chennai")
        assert resp_chennai.status_code == 200
        data_c = resp_chennai.json()
        assert "Chennai" in data_c["display_name"]
        assert 12.5 < data_c["latitude"] < 13.5
        assert 79.5 < data_c["longitude"] < 80.5
        assert data_c["attribution"] is not None

        # Unknown location
        resp_unknown = await ac.get("/api/v1/providers/geocode?query=NonExistentPlaceXYZ999")
        assert resp_unknown.status_code == 404


@pytest.mark.asyncio
async def test_rbac_admin_seed():
    """Verify RBAC on administrative provider seeding endpoint."""
    from app.api.deps import get_current_user
    from app.models.user import User

    uid = uuid.uuid4().hex[:8]
    user_email = f"test_provider_user_{uid}@example.com"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Unauthenticated -> 401
        unauth_resp = await ac.post("/api/v1/providers/seed")
        assert unauth_resp.status_code == 401

        # 2. Register normal user
        reg_res = await ac.post(
            "/api/v1/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Provider Test User"},
        )
        assert reg_res.status_code == 201
        user_token = reg_res.json()["access_token"]

        # Normal user -> 403 Forbidden
        user_resp = await ac.post(
            "/api/v1/providers/seed",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert user_resp.status_code == 403
        assert "Operation not permitted" in user_resp.json()["detail"]

        # 3. Admin user -> 200 OK via admin dependency override
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
                "/api/v1/providers/seed",
                headers={"Authorization": "Bearer mocked_admin_token"},
            )
            assert admin_resp.status_code == 200
            stats = admin_resp.json()
            assert stats["status"] == "SUCCESS"
            assert "facilities_ingested" in stats
            assert "doctors_ingested" in stats
        finally:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_privacy_audit_logging_masks_precise_coordinates():
    """Verify that provider search logs search terms but never logs precise user latitude/longitude."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.get(
            "/api/v1/providers/search",
            params={
                "lat": 13.060412345,
                "lon": 80.249612345,
                "city": "Chennai",
                "specialty": "Cardiology",
            },
        )

    # Check AuditLog in database
    async with AsyncSessionLocal() as session:
        query = (
            select(AuditLog)
            .where(AuditLog.action == "PROVIDER_SEARCH")
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
        result = await session.execute(query)
        log_entry = result.scalar_one_or_none()

        assert log_entry is not None
        details = log_entry.details or {}
        # Confirm city, specialty, and radius are recorded
        assert details.get("city") == "Chennai"
        assert details.get("specialty") == "Cardiology"
        # CRITICAL PRIVACY CHECK: Precise coordinates MUST NOT be stored in audit logs
        assert "lat" not in details
        assert "lon" not in details
        assert "13.060412345" not in str(details)
        assert "80.249612345" not in str(details)
        assert "13.060412345" not in str(details)
        assert "80.249612345" not in str(details)
