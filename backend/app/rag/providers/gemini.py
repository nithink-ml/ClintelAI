"""Gemini LLM Provider for evidence-grounded clinical synthesis."""

import logging
import re
from typing import Any

import httpx

from app.core.config import settings
from app.rag.models import Citation, EvidenceChunk
from app.rag.providers.base import BaseLLMProvider
from app.rag.providers.mock import MockGroundedProvider
from app.rag.safety import MedicalSafetyEngine

logger = logging.getLogger("clintelai")


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM Provider implementing strict clinical prompt constraints and fallback."""

    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    def __init__(self, api_key: str | None = None, model: str = "gemini-1.5-flash"):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model
        self._fallback_provider = MockGroundedProvider()

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        """Returns True if a non-empty API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def _build_grounding_prompt(
        self,
        query: str,
        evidence: list[tuple[EvidenceChunk, float]],
        language: str = "en",
    ) -> str:
        """Constructs an evidence-constrained clinical prompt."""
        evidence_block_lines = []
        for idx, (chunk, score) in enumerate(evidence, start=1):
            clean_body = re.sub(r"^\[.*?\]\n?", "", chunk.content).strip()
            evidence_block_lines.append(
                f"[Source {idx}]: {chunk.source_name} - {chunk.title} ({chunk.section_title})\n{clean_body}\n"
            )

        evidence_text = "\n".join(evidence_block_lines)

        return (
            "You are ClintelAI, an evidence-grounded healthcare intelligence platform.\n"
            "CRITICAL MEDICAL SAFETY & GROUNDING RULES:\n"
            "1. You must ONLY formulate your answer using the authoritative evidence provided below.\n"
            "2. Do NOT diagnose medical conditions, and do NOT prescribe specific drug dosages.\n"
            "3. Attribute every factual claim to its source using bracketed numbers, e.g., [1], [2].\n"
            "4. If the evidence is insufficient to answer the user's question safely, state that authoritative clinical "
            "evidence is insufficient and recommend consulting a registered doctor.\n"
            f"5. Respond in the requested language: '{language}'.\n\n"
            f"AUTHORITATIVE CLINICAL EVIDENCE:\n{evidence_text}\n\n"
            f"PATIENT / USER QUERY:\n{query}\n\n"
            "EVIDENCE-GROUNDED RESPONSE WITH CITATIONS:"
        )

    def generate_grounded_response(
        self,
        query: str,
        evidence: list[tuple[EvidenceChunk, float]],
        language: str = "en",
        emergency_detected: bool = False,
    ) -> tuple[str, list[Citation], bool, str | None]:
        # 1. Abstention check if no evidence
        if not evidence or len(evidence) == 0:
            return self._fallback_provider.generate_grounded_response(
                query, evidence, language, emergency_detected
            )

        # 2. If API key is not configured or in offline mode, fall back to deterministic mock provider
        if not self.is_available:
            logger.info("GEMINI_API_KEY not configured. Falling back to deterministic grounded synthesis.")
            return self._fallback_provider.generate_grounded_response(
                query, evidence, language, emergency_detected
            )

        # 3. Build citations list from verified retrieved evidence
        citations: list[Citation] = []
        for idx, (chunk, score) in enumerate(evidence, start=1):
            clean_body = re.sub(r"^\[.*?\]\n?", "", chunk.content).strip()
            sentences = re.split(r"(?<=[.!?])\s+", clean_body)
            snippet = " ".join(sentences[:2]) if len(sentences) >= 2 else clean_body[:200]
            citations.append(
                Citation(
                    citation_index=idx,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    source_name=chunk.source_name,
                    authority_tier=chunk.authority_tier,
                    title=chunk.title,
                    section_title=chunk.section_title,
                    url=chunk.url,
                    published_date=chunk.published_date,
                    snippet=snippet,
                    relevance_score=score,
                )
            )

        # 4. Attempt Gemini API call
        prompt = self._build_grounding_prompt(query, evidence, language)
        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        payload: dict[str, Any] = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,  # Low temperature for strict factual adherence
                "maxOutputTokens": 1024,
            },
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                    params=params,
                    headers=headers,
                    json=payload,
                )
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        raw_text = (
                            candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        )
                        if raw_text.strip():
                            sanitized = MedicalSafetyEngine.sanitize_medical_text(raw_text.strip())
                            return sanitized, citations, False, None

                logger.warning(
                    f"Gemini API returned status {res.status_code}: {res.text[:100]}. Falling back to mock generator."
                )
        except Exception as exc:
            logger.warning(f"Gemini API invocation failed ({exc!s}). Falling back to mock generator.")

        # Graceful degradation fallback
        return self._fallback_provider.generate_grounded_response(
            query, evidence, language, emergency_detected
        )
