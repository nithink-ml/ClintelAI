"""Comprehensive Test Suite for Gemini Provider Abstraction, Fallback Safety, and Emergency Precedence."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.core.config import settings
from app.rag.models import EvidenceChunk, RAGQueryRequest
from app.rag.pipeline import RAGPipeline
from app.rag.providers import (
    GeminiProvider,
    MockGroundedProvider,
    get_llm_provider,
)


@pytest.fixture
def sample_evidence():
    return [
        (
            EvidenceChunk(
                chunk_id="chk_001",
                document_id="doc_dengue_who",
                source_name="World Health Organization",
                authority_tier="TIER_1_GLOBAL_AUTHORITY",
                title="Dengue Clinical Management Guidelines",
                section_title="Symptomatic Management",
                url="https://who.int/dengue",
                published_date="2024-01-15",
                content="Paracetamol is recommended for fever and pain management in dengue. NSAIDs such as ibuprofen and aspirin should be avoided due to hemorrhage risk.",
                keywords=["dengue", "paracetamol", "nsaids"],
            ),
            0.88,
        ),
        (
            EvidenceChunk(
                chunk_id="chk_002",
                document_id="doc_dengue_icmr",
                source_name="Indian Council of Medical Research",
                authority_tier="TIER_1_NATIONAL_STATUTORY",
                title="National Guidelines for Clinical Management of Dengue Fever",
                section_title="Hydration Protocols",
                url="https://icmr.gov.in/dengue",
                published_date="2024-03-20",
                content="Adequate oral hydration with ORS and tender coconut water is vital during the critical phase of dengue.",
                keywords=["dengue", "hydration", "ors"],
            ),
            0.82,
        ),
    ]


def test_provider_factory_resolution():
    """Verifies that the factory instantiates the correct provider based on configuration."""
    mock_p = get_llm_provider("mock")
    assert isinstance(mock_p, MockGroundedProvider)
    assert mock_p.provider_name == "mock"

    gemini_p = get_llm_provider("gemini")
    assert isinstance(gemini_p, GeminiProvider)
    assert gemini_p.provider_name == "gemini"


def test_gemini_unavailable_fallback_disabled_missing_key(sample_evidence):
    """Case A/D: Missing API key with fallback disabled (production default) returns controlled degraded response."""
    gemini_p = GeminiProvider(api_key="", fallback_enabled=False)
    assert gemini_p.is_available is False
    assert gemini_p.fallback_enabled is False

    res = gemini_p.generate_grounded_response(
        query="What medicine is safe for dengue fever?",
        evidence=sample_evidence,
        language="en",
    )

    ans, citations, abstained, reason = res[:4]

    # Must NOT silently return a mock response
    assert abstained is True
    assert reason == "GEMINI_API_KEY_MISSING"
    assert res.fallback_used is False
    assert res.generation_mode == "CONTROLLED_DEGRADED"
    assert res.llm_provider == "gemini"

    # Must provide clear degraded notice
    assert "AI Clinical Synthesis Temporarily Unavailable" in ans
    assert "production fallback is disabled" in ans

    # Must retain retrieved evidence citations so evidence is not lost
    assert len(citations) == 2
    assert citations[0].source_name == "World Health Organization"


def test_gemini_unavailable_fallback_enabled_missing_key(sample_evidence):
    """Case B/D: Missing API key with fallback enabled executes mock fallback and flags fallback_used=True."""
    gemini_p = GeminiProvider(api_key="", fallback_enabled=True)
    assert gemini_p.is_available is False
    assert gemini_p.fallback_enabled is True

    res = gemini_p.generate_grounded_response(
        query="What medicine is safe for dengue fever?",
        evidence=sample_evidence,
        language="en",
    )

    ans, citations, abstained, _reason = res[:4]

    assert abstained is False
    assert res.fallback_used is True
    assert res.generation_mode == "FALLBACK_MOCK"
    assert res.llm_provider == "gemini"
    assert len(citations) == 2
    assert "Paracetamol" in ans


def test_gemini_network_failure_fallback_disabled(sample_evidence):
    """Case E: Network connection failure with fallback disabled returns controlled degraded response."""
    gemini_p = GeminiProvider(api_key="valid-mock-key-for-test", fallback_enabled=False)

    with patch("httpx.Client.post", side_effect=httpx.ConnectError("Network unreachable")):
        res = gemini_p.generate_grounded_response(
            query="What medicine is safe for dengue fever?",
            evidence=sample_evidence,
            language="en",
        )

    ans, citations, abstained, reason = res[:4]
    assert abstained is True
    assert reason == "GEMINI_NETWORK_UNAVAILABLE"
    assert res.fallback_used is False
    assert res.generation_mode == "CONTROLLED_DEGRADED"
    assert "AI Clinical Synthesis Temporarily Unavailable" in ans
    assert len(citations) == 2


def test_gemini_network_failure_fallback_enabled(sample_evidence):
    """Case E: Network connection failure with fallback enabled falls back to mock generator."""
    gemini_p = GeminiProvider(api_key="valid-mock-key-for-test", fallback_enabled=True)

    with patch("httpx.Client.post", side_effect=httpx.ConnectTimeout("Request timed out")):
        res = gemini_p.generate_grounded_response(
            query="What medicine is safe for dengue fever?",
            evidence=sample_evidence,
            language="en",
        )

    ans, citations, abstained, _reason = res[:4]
    assert abstained is False
    assert res.fallback_used is True
    assert res.generation_mode == "FALLBACK_MOCK"
    assert len(citations) == 2
    assert "Paracetamol" in ans


def test_gemini_api_http_error_fallback_disabled(sample_evidence):
    """Case E: Gemini API returns HTTP 503 error with fallback disabled returns controlled degraded response."""
    gemini_p = GeminiProvider(api_key="valid-mock-key-for-test", fallback_enabled=False)

    mock_resp = MagicMock()
    mock_resp.status_code = 503
    mock_resp.text = "Service Unavailable"

    with patch("httpx.Client.post", return_value=mock_resp):
        res = gemini_p.generate_grounded_response(
            query="What medicine is safe for dengue fever?",
            evidence=sample_evidence,
            language="en",
        )

    ans, citations, abstained, reason = res[:4]
    assert abstained is True
    assert reason == "GEMINI_API_ERROR"
    assert res.fallback_used is False
    assert res.generation_mode == "CONTROLLED_DEGRADED"
    assert "AI Clinical Synthesis Temporarily Unavailable" in ans
    assert len(citations) == 2


def test_gemini_api_http_error_fallback_enabled(sample_evidence):
    """Case E: Gemini API returns HTTP 500 error with fallback enabled falls back to mock generator."""
    gemini_p = GeminiProvider(api_key="valid-mock-key-for-test", fallback_enabled=True)

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch("httpx.Client.post", return_value=mock_resp):
        res = gemini_p.generate_grounded_response(
            query="What medicine is safe for dengue fever?",
            evidence=sample_evidence,
            language="en",
        )

    ans, citations, abstained, _reason = res[:4]
    assert abstained is False
    assert res.fallback_used is True
    assert res.generation_mode == "FALLBACK_MOCK"
    assert len(citations) == 2
    assert "Paracetamol" in ans


def test_gemini_successful_response(sample_evidence):
    """Case C: Successful Gemini API call produces evidence-grounded response with GEMINI_DIRECT mode."""
    gemini_p = GeminiProvider(api_key="valid-mock-key-for-test", fallback_enabled=False)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": "According to the World Health Organization guidelines, paracetamol is recommended for fever management [1]. Adequate hydration with ORS should be maintained [2]."
                        }
                    ]
                }
            }
        ]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        res = gemini_p.generate_grounded_response(
            query="What medicine is safe for dengue fever?",
            evidence=sample_evidence,
            language="en",
        )

    ans, citations, abstained, reason = res[:4]
    assert abstained is False
    assert reason is None
    assert res.fallback_used is False
    assert res.generation_mode == "GEMINI_DIRECT"
    assert res.llm_provider == "gemini"
    assert len(citations) == 2
    assert "paracetamol" in ans.lower()
    assert "[1]" in ans


@pytest.mark.asyncio
async def test_emergency_escalation_takes_precedence_even_when_gemini_degraded():
    """Verify that acute emergency red flags take top priority even when Gemini is degraded and fallback is disabled."""
    pipeline = RAGPipeline.get_instance()
    if not pipeline.is_initialized:
        await pipeline.initialize()

    # Query with life-threatening emergency
    emergency_query = "severe crushing chest pain radiating to left arm and shortness of breath"

    # Temporarily configure Gemini provider with degraded fallback disabled
    original_provider = settings.LLM_PROVIDER
    original_fallback = settings.LLM_FALLBACK_ENABLED
    try:
        settings.LLM_PROVIDER = "gemini"
        settings.LLM_FALLBACK_ENABLED = False

        from app.rag.providers.factory import _CACHED_PROVIDERS

        _CACHED_PROVIDERS["gemini"] = GeminiProvider(api_key="", fallback_enabled=False)

        req = RAGQueryRequest(query=emergency_query, language="en")
        response = await pipeline.query(req)

        # EMERGENCY PRECEDENCE: Must be flagged as EMERGENCY_ESCALATION regardless of LLM status
        assert response.emergency.is_emergency is True
        assert response.medical_safety_level == "EMERGENCY_ESCALATION"
        assert "112" in response.emergency.emergency_numbers
        assert "108" in response.emergency.emergency_numbers
        assert response.abstained is True
        assert response.abstention_reason == "GEMINI_API_KEY_MISSING"
        assert response.fallback_used is False
        assert response.retrieval_metadata.generation_mode == "CONTROLLED_DEGRADED"
    finally:
        settings.LLM_PROVIDER = original_provider
        settings.LLM_FALLBACK_ENABLED = original_fallback
        _CACHED_PROVIDERS.pop("gemini", None)


def test_gemini_provider_prompt_grounding_structure(sample_evidence):
    """Verifies that Gemini prompt strictly mandates source attribution and forbids diagnostic extrapolation."""
    gemini_p = GeminiProvider(api_key="test-api-key-do-not-call")
    prompt = gemini_p._build_grounding_prompt(
        query="What medicine is safe for dengue fever?",
        evidence=sample_evidence,
        language="ta",
    )

    assert "You must ONLY formulate your answer using the authoritative evidence provided below." in prompt
    assert "Do NOT diagnose medical conditions, and do NOT prescribe specific drug dosages." in prompt
    assert "Attribute every factual claim to its source using bracketed numbers" in prompt
    assert "Respond in the requested language: 'ta'" in prompt
    assert "World Health Organization" in prompt
    assert "Indian Council of Medical Research" in prompt


def test_gemini_api_key_environment_safety():
    """Ensures that the Gemini API key is managed exclusively via settings and is never exposed."""
    assert hasattr(settings, "GEMINI_API_KEY")
    assert hasattr(settings, "LLM_FALLBACK_ENABLED")
    from app.schemas.health import HealthResponse

    assert "GEMINI_API_KEY" not in HealthResponse.model_fields
    assert "api_key" not in HealthResponse.model_fields
