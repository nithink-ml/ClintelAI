"""Integration and API tests for Clinical RAG endpoints, citations, abstention, safety, and audit logging."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_user
from app.api.v1.rag import sanitize_query_for_audit
from app.main import app
from app.models.user import User


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_rag_query_clinical_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/rag/query",
            json={
                "query": "What are the fluid management guidelines for dengue?",
                "language": "en",
                "max_evidence_chunks": 3,
            },
        )
    assert response.status_code == 200
    data = response.json()

    assert data["query"] == "What are the fluid management guidelines for dengue?"
    assert data["abstained"] is False
    assert len(data["citations"]) >= 1
    assert data["confidence_score"] > 0.50
    assert "Medical Disclaimer" in data["safety_disclaimer"]
    assert data["emergency"]["is_emergency"] is False

    citation = data["citations"][0]
    assert citation["citation_index"] == 1
    assert any(
        src in citation["source_name"]
        for src in [
            "World Health Organization",
            "Indian Council of Medical Research",
            "Ministry of Health and Family Welfare",
            "PubMed Central",
        ]
    )
    assert citation["url"].startswith("http")


@pytest.mark.asyncio
async def test_rag_query_emergency_escalation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/rag/query",
            json={
                "query": "Patient experiencing severe crushing chest pain radiating to the left arm and jaw",
                "language": "en",
            },
        )
    assert response.status_code == 200
    data = response.json()

    assert data["emergency"]["is_emergency"] is True
    assert data["emergency"]["level"] == "CRITICAL"
    assert "112" in data["emergency"]["emergency_numbers"]
    assert "108" in data["emergency"]["emergency_numbers"]
    assert "IMMEDIATE EMERGENCY ACTION REQUIRED" in data["emergency"]["action_message"]


@pytest.mark.asyncio
async def test_rag_query_abstention_on_ungrounded_query():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/rag/query",
            json={
                "query": "How do I invest in real estate tokens on the blockchain?",
                "language": "en",
            },
        )
    assert response.status_code == 200
    data = response.json()

    assert data["abstained"] is True
    assert data["citations"] == []
    assert data["confidence_score"] == 0.0
    assert "Insufficient authoritative clinical evidence" in data["answer"]


@pytest.mark.asyncio
async def test_rag_sources_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/rag/sources")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "SUCCESS"
    assert data["total_documents"] >= 10
    assert data["total_chunks"] >= 30
    assert len(data["sources"]) >= 10

    source_names = {s["source_name"] for s in data["sources"]}
    assert "World Health Organization" in source_names
    assert "Indian Council of Medical Research" in source_names


@pytest.mark.asyncio
async def test_rag_reindex_role_authorization():
    uid = uuid.uuid4().hex[:8]
    user_email = f"rag_user_{uid}@example.com"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Unauthenticated request -> 401
        res_unauth = await ac.post("/api/v1/rag/ingest")
        assert res_unauth.status_code == 401

        # Register normal user
        reg_res = await ac.post(
            "/api/v1/auth/register",
            json={"email": user_email, "password": "Password123!", "full_name": "Normal User"},
        )
        assert reg_res.status_code == 201
        user_token = reg_res.json()["access_token"]
        from app.core.security import decode_token

        real_user_id = uuid.UUID(decode_token(user_token)["sub"])

        # 2. Regular user -> 403 Forbidden on admin endpoint
        res_forbidden = await ac.post(
            "/api/v1/rag/ingest",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res_forbidden.status_code == 403

        # 3. Admin user -> 200 OK via authenticated admin
        mock_admin = User(
            id=real_user_id,
            email=user_email,
            role="admin",
            is_active=True,
        )
        app.dependency_overrides[get_current_user] = lambda: mock_admin
        try:
            res_admin = await ac.post(
                "/api/v1/rag/ingest",
                headers={"Authorization": "Bearer mocked_admin_token"},
            )
            assert res_admin.status_code == 200
            assert res_admin.json()["status"] == "SUCCESS"
        finally:
            app.dependency_overrides.pop(get_current_user, None)


def test_sanitize_query_for_audit():
    masked = sanitize_query_for_audit("Contact me at user@health.org or 9876543210 for emergency")
    assert "user@health.org" not in masked
    assert "[EMAIL_MASKED]" in masked
    assert "9876543210" not in masked
    assert "[PHONE_MASKED]" in masked


@pytest.mark.asyncio
async def test_rag_query_audit_privacy_masking():
    transport = ASGITransport(app=app)
    sensitive_query = "My child at patient.care@clinic.com with phone 9876543210 has dengue fever"

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/rag/query",
            json={"query": sensitive_query, "language": "en"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == sensitive_query
    # Check that sanitizer properly handles this query
    masked = sanitize_query_for_audit(sensitive_query)
    assert "patient.care@clinic.com" not in masked
    assert "[EMAIL_MASKED]" in masked
    assert "9876543210" not in masked
    assert "[PHONE_MASKED]" in masked
