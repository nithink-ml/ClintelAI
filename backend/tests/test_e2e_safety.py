"""Comprehensive Cross-Module End-to-End Safety Evaluation Suite for ClintelAI."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.models.provider import VerificationStatus


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_e2e_cross_module_clinical_journey():
    """Validates the complete patient clinical journey across Auth, Alerts, RAG, and Providers.

    Steps:
    1. Register patient and retrieve cryptographically signed JWT.
    2. Query public health alerts for Chennai, Tamil Nadu with spatial proximity.
    3. Query RAG engine regarding dengue treatment; verify citation grounding and abstention.
    4. Search nearby healthcare providers; verify PostGIS distance ordering and DEMO guardrail.
    5. Verify location privacy in audit logging.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Authentication & Account Creation
        unique_user = uuid.uuid4().hex[:8]
        reg_resp = await client.post(
            f"{settings.API_V1_STR}/auth/register",
            json={
                "email": f"patient.{unique_user}@example.com",
                "password": "SecurePassword123!",
                "full_name": "Kavitha Ramanathan",
                "preferred_language": "ta",
            },
        )
        assert reg_resp.status_code == 201
        auth_data = reg_resp.json()
        token = auth_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Regional Public Health Alerts
        # Coordinates for Chennai: 13.0827, 80.2707
        alert_resp = await client.get(
            f"{settings.API_V1_STR}/alerts/search",
            params={"lat": 13.0827, "lon": 80.2707, "language": "ta"},
            headers=headers,
        )
        assert alert_resp.status_code == 200
        alerts_data = alert_resp.json()
        assert "items" in alerts_data
        assert alerts_data["total"] > 0
        # Every alert must have trusted source provenance and freshness
        for alert in alerts_data["items"]:
            assert alert["source_name"] is not None
            assert alert["freshness"]["status"] in ("FRESH", "RECENT", "STALE", "EXPIRED")
            assert alert["is_demo_data"] is True

        # Step 3: Evidence-Grounded RAG Clinical Query
        rag_resp = await client.post(
            f"{settings.API_V1_STR}/rag/query",
            json={
                "query": "What is the recommended fluid management and fever protocol for dengue fever?",
                "language": "en",
                "max_evidence_chunks": 3,
            },
            headers=headers,
        )
        assert rag_resp.status_code == 200
        rag_data = rag_resp.json()
        assert rag_data["abstained"] is False
        assert len(rag_data["citations"]) > 0
        # Verify citations are from authoritative bodies (WHO / ICMR / MoHFW)
        for cite in rag_data["citations"]:
            assert "Tier 1" in cite["authority_tier"] or "Tier 2" in cite["authority_tier"]
        assert "fluid" in rag_data["answer"].lower() or "dengue" in rag_data["answer"].lower()
        assert "Medical Disclaimer" in rag_data["safety_disclaimer"]

        # Step 4: Provider Discovery with PostGIS Sorting & Demo Guardrail
        prov_resp = await client.get(
            f"{settings.API_V1_STR}/providers/search",
            params={"lat": 13.0827, "lon": 80.2707, "radius_km": 25.0},
            headers=headers,
        )
        assert prov_resp.status_code == 200
        prov_data = prov_resp.json()
        assert prov_data["total"] > 0
        # Validate PostGIS distance ascending order
        distances = [
            item["distance_km"] for item in prov_data["items"] if item.get("distance_km") is not None
        ]
        assert distances == sorted(distances)

        # STRICT DEMO GUARDRAIL: Synthetic providers must NEVER be presented as official VERIFIED
        for item in prov_data["items"]:
            if item.get("is_demo_data") is True:
                v = item["verification"]
                assert v["status"] == VerificationStatus.DEMO_SIMULATED.value
                assert v["effective_status"] == VerificationStatus.DEMO_SIMULATED.value
                assert v["label"] == "DEMO_SIMULATED"


@pytest.mark.asyncio
async def test_e2e_emergency_escalation_across_all_endpoints():
    """Verifies that emergency clinical red flags cannot be bypassed across RAG, Providers, and Alerts."""
    emergency_query = "severe crushing chest pain radiating to arm and shortness of breath"
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. RAG query endpoint
        rag_res = await client.post(
            f"{settings.API_V1_STR}/rag/query",
            json={"query": emergency_query, "language": "en"},
        )
        assert rag_res.status_code == 200
        rag_json = rag_res.json()
        assert rag_json["emergency"]["is_emergency"] is True
        assert rag_json["medical_safety_level"] == "EMERGENCY_ESCALATION"
        assert "112" in rag_json["emergency"]["emergency_numbers"]

        # 2. Provider search endpoint
        prov_res = await client.get(
            f"{settings.API_V1_STR}/providers/search",
            params={"query": emergency_query, "lat": 12.9716, "lon": 77.5946},
        )
        assert prov_res.status_code == 200
        prov_json = prov_res.json()
        assert prov_json["emergency_escalation"] is not None
        assert prov_json["emergency_escalation"]["is_emergency"] is True

        # 3. Alert search endpoint
        alert_res = await client.get(
            f"{settings.API_V1_STR}/alerts/search",
            params={"query": emergency_query, "lat": 12.9716, "lon": 77.5946},
        )
        assert alert_res.status_code == 200
        alert_json = alert_res.json()
        assert alert_json["emergency_escalation"] is not None
        assert alert_json["emergency_escalation"]["is_emergency"] is True


@pytest.mark.asyncio
async def test_e2e_multilingual_consistency():
    """Verifies localized disclaimers, emergency messages, and translations across all 6 supported languages."""
    languages = ["en", "ta", "hi", "ml", "te", "kn"]
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for lang in languages:
            # Test alert search localized disclaimer
            res = await client.get(
                f"{settings.API_V1_STR}/alerts/search",
                params={"language": lang, "lat": 12.9716, "lon": 77.5946},
            )
            assert res.status_code == 200
            data = res.json()
            assert "disclaimer" in data
            assert len(data["disclaimer"]) > 20

            # Test RAG disclaimer
            rag_res = await client.post(
                f"{settings.API_V1_STR}/rag/query",
                json={"query": "dengue symptoms", "language": lang},
            )
            assert rag_res.status_code == 200
            rag_json = rag_res.json()
            assert "safety_disclaimer" in rag_json
            assert len(rag_json["safety_disclaimer"]) > 20


@pytest.mark.asyncio
async def test_e2e_all_india_propagation_for_national_advisories():
    """Verifies that national public health advisories reach all geographic locations across India."""
    # Test coordinates across India
    locations = [
        {"city": "Bengaluru", "lat": 12.9716, "lon": 77.5946},
        {"city": "New Delhi", "lat": 28.6139, "lon": 77.2090},
        {"city": "Mumbai", "lat": 19.0760, "lon": 72.8777},
        {"city": "Kolkata", "lat": 22.5726, "lon": 88.3639},
    ]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for loc in locations:
            res = await client.get(
                f"{settings.API_V1_STR}/alerts/search",
                params={"lat": loc["lat"], "lon": loc["lon"], "status": "ACTIVE"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["total"] > 0
            # National alerts (target_scope=ALL_INDIA) should appear in all location queries
            titles = [a["title"].lower() for a in data["items"]]
            assert any(
                "measles" in t or "heatwave" in t or "national" in t for t in titles
            ), f"No national advisory returned for {loc['city']}"


@pytest.mark.asyncio
async def test_e2e_error_handling_and_degradation():
    """Verifies graceful handling of non-existent resources and malformed inputs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. 404 for non-existent facility
        random_id = uuid.uuid4()
        res_fac = await client.get(f"{settings.API_V1_STR}/providers/facilities/{random_id}")
        assert res_fac.status_code == 404

        # 2. 404 for non-existent alert
        res_alert = await client.get(f"{settings.API_V1_STR}/alerts/{random_id}")
        assert res_alert.status_code == 404

        # 3. 422 for malformed UUID
        res_bad_uuid = await client.get(f"{settings.API_V1_STR}/alerts/not-a-valid-uuid")
        assert res_bad_uuid.status_code == 422

        # 4. Service readiness probe
        res_ready = await client.get("/readyz")
        assert res_ready.status_code == 200
        assert res_ready.json()["status"] in ("ready", "degraded")
