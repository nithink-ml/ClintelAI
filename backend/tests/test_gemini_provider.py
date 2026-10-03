"""Tests for Gemini Provider Abstraction and Grounding Architecture."""

import pytest

from app.core.config import settings
from app.rag.models import EvidenceChunk
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


def test_gemini_provider_offline_fallback(sample_evidence):
    """Verifies that GeminiProvider gracefully falls back to deterministic grounding when API key is empty."""
    gemini_p = GeminiProvider(api_key="")
    assert gemini_p.is_available is False

    ans, citations, abstained, _reason = gemini_p.generate_grounded_response(
        query="What medicine is safe for dengue fever?",
        evidence=sample_evidence,
        language="en",
    )

    assert abstained is False
    assert len(citations) == 2
    assert citations[0].source_name == "World Health Organization"
    assert "Paracetamol" in ans
    assert "[1]" in ans


def test_gemini_provider_prompt_grounding_structure(sample_evidence):
    """Verifies that Gemini prompt strictly mandates source attribution and forbids diagnostic extrapolation."""
    gemini_p = GeminiProvider(api_key="test-api-key-do-not-call")
    prompt = gemini_p._build_grounding_prompt(
        query="What medicine is safe for dengue fever?",
        evidence=sample_evidence,
        language="ta",
    )

    # Validate strict clinical constraints inside the constructed prompt
    assert "You must ONLY formulate your answer using the authoritative evidence provided below." in prompt
    assert "Do NOT diagnose medical conditions, and do NOT prescribe specific drug dosages." in prompt
    assert "Attribute every factual claim to its source using bracketed numbers" in prompt
    assert "Respond in the requested language: 'ta'" in prompt
    assert "World Health Organization" in prompt
    assert "Indian Council of Medical Research" in prompt


def test_gemini_api_key_environment_safety():
    """Ensures that the Gemini API key is managed exclusively via settings and is never exposed."""
    # Settings must have GEMINI_API_KEY attribute
    assert hasattr(settings, "GEMINI_API_KEY")
    # Verify key does not leak into any public models or representations
    from app.schemas.health import HealthResponse
    assert "GEMINI_API_KEY" not in HealthResponse.model_fields
    assert "api_key" not in HealthResponse.model_fields
