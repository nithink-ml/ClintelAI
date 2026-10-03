"""Test Suite for Phase 6 Production Readiness, Invariants, and Abuse Protection."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request, Response

from app.core.config import Settings, settings
from app.core.rate_limit import _IN_MEMORY_RATE_LIMITS, RateLimiter
from app.rag.models import EvidenceChunk, RAGQueryRequest
from app.rag.pipeline import RAGPipeline
from app.rag.providers.gemini import GeminiProvider


def test_production_settings_validation_enforced():
    """Verify that Settings validates critical production security invariants."""
    # 1. Reject DEBUG=True in production
    with pytest.raises(ValueError, match="DEBUG must be False in production"):
        Settings(ENVIRONMENT="production", DEBUG=True, SECRET_KEY="a" * 32)

    # 2. Reject insecure default SECRET_KEY
    with pytest.raises(ValueError, match="SECRET_KEY is insecure or too short"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="insecure-dev-secret-key-change-me-in-production-minimum-32-chars",
        )

    # 3. Reject short SECRET_KEY
    with pytest.raises(ValueError, match="SECRET_KEY is insecure or too short"):
        Settings(ENVIRONMENT="production", DEBUG=False, SECRET_KEY="short-key")

    # 4. Reject LLM_FALLBACK_ENABLED=True in production
    with pytest.raises(ValueError, match="LLM_FALLBACK_ENABLED must be False in production"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="a" * 32,
            LLM_FALLBACK_ENABLED=True,
        )

    # 5. Reject wildcard CORS in production
    with pytest.raises(ValueError, match="Wildcard CORS origin"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="a" * 32,
            LLM_FALLBACK_ENABLED=False,
            CORS_ORIGINS=["*"],
        )

    # 6. Valid production configuration passes
    prod_settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="production-cryptographically-secure-key-32chars",
        LLM_FALLBACK_ENABLED=False,
        CORS_ORIGINS=["https://clintelai.example.com"],
    )
    assert prod_settings.ENVIRONMENT == "production"
    assert prod_settings.DEBUG is False
    assert prod_settings.LLM_FALLBACK_ENABLED is False


@pytest.mark.asyncio
async def test_rate_limiter_in_memory_sliding_window():
    """Verifies that RateLimiter tracks requests and enforces HTTP 429 when exceeded."""
    limiter = RateLimiter(requests=3, window_seconds=60, prefix="test_limit")
    _IN_MEMORY_RATE_LIMITS.clear()

    # Create mock request and response
    mock_request = MagicMock(spec=Request)
    mock_request.headers = {"X-Forwarded-For": "203.0.113.195"}
    mock_request.client = None
    mock_response = Response()

    with (
        patch("app.core.rate_limit.get_redis_client", return_value=None),
        patch.object(settings, "RATE_LIMIT_ENABLED", True),
    ):
            # Requests 1, 2, 3 should succeed
            for i in range(1, 4):
                await limiter(mock_request, mock_response)
                assert mock_response.headers["X-RateLimit-Limit"] == "3"
                assert int(mock_response.headers["X-RateLimit-Remaining"]) == 3 - i

            # Request 4 should be rejected with 429
            with pytest.raises(HTTPException) as exc_info:
                await limiter(mock_request, mock_response)

            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in exc_info.value.detail
            assert "Retry-After" in exc_info.value.headers


def test_production_db_pool_configuration():
    """Verifies that database pool settings are present with production-grade defaults."""
    assert hasattr(settings, "DB_POOL_SIZE")
    assert hasattr(settings, "DB_MAX_OVERFLOW")
    assert hasattr(settings, "DB_POOL_TIMEOUT")
    assert hasattr(settings, "DB_POOL_RECYCLE")
    assert settings.DB_POOL_SIZE >= 5
    assert settings.DB_MAX_OVERFLOW >= 10
    assert settings.DB_POOL_RECYCLE <= 3600


def test_live_gemini_production_contract():
    """Verifies that GeminiProvider defaults to the current active model and fallback_enabled=False."""
    gemini = GeminiProvider(fallback_enabled=False)
    assert gemini.model == "gemini-flash-latest"
    assert gemini.fallback_enabled is False


def test_controlled_degradation_when_gemini_unavailable():
    """Verifies that when Gemini is unavailable in production, it strictly degrades without silent mock."""
    gemini = GeminiProvider(api_key="", fallback_enabled=False)
    evidence = [
        (
            EvidenceChunk(
                chunk_id="c1",
                document_id="d1",
                source_name="WHO",
                authority_tier="TIER_1_GLOBAL_AUTHORITY",
                title="Dengue Management",
                section_title="Fever Care",
                url="https://who.int",
                published_date="2024-01-01",
                content="Paracetamol is recommended for fever.",
                keywords=["dengue"],
            ),
            0.85,
        )
    ]

    res = gemini.generate_grounded_response(
        query="What medicine for dengue fever?",
        evidence=evidence,
        language="en",
    )

    assert res.abstained is True
    assert res.fallback_used is False
    assert res.generation_mode == "CONTROLLED_DEGRADED"
    assert "AI Clinical Synthesis Temporarily Unavailable" in res.answer
    assert len(res.citations) == 1
    assert res.citations[0].source_name == "WHO"


@pytest.mark.asyncio
async def test_emergency_escalation_takes_precedence_in_production():
    """Verifies that acute medical emergencies take immediate priority under production settings."""
    pipeline = RAGPipeline.get_instance()
    await pipeline.initialize()

    req = RAGQueryRequest(
        query="severe crushing chest pain radiating to left jaw, difficulty breathing",
        language="en",
    )
    res = await pipeline.query(req)

    assert res.emergency.is_emergency is True
    assert res.medical_safety_level == "EMERGENCY_ESCALATION"
    assert "112" in res.emergency.emergency_numbers
    assert "108" in res.emergency.emergency_numbers
