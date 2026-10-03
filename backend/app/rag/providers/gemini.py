"""Gemini LLM Provider for evidence-grounded clinical synthesis with configurable fallback."""

import logging
import re
from typing import Any

import httpx

from app.core.config import settings
from app.rag.models import Citation, EvidenceChunk, GroundedResponse
from app.rag.providers.base import BaseLLMProvider
from app.rag.providers.mock import MockGroundedProvider
from app.rag.safety import MedicalSafetyEngine

logger = logging.getLogger("clintelai")


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM Provider implementing strict clinical prompt constraints and configurable fallback."""

    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    MULTILINGUAL_DEGRADED_MESSAGES = {
        "en": (
            "AI Clinical Synthesis Temporarily Unavailable: The primary generative clinical intelligence "
            "service (Google Gemini) is currently unavailable or unconfigured, and production fallback is disabled "
            "to prevent unverified synthesis. Please review the authoritative guideline citations below or consult "
            "a registered healthcare professional."
        ),
        "ta": (
            "செயற்கை நுண்ணறிவு மருத்துவ சுருக்கம் தற்காலிகமாக கிடைக்கவில்லை: முதன்மை மருத்துவ நுண்ணறிவு சேவை "
            "(Google Gemini) தற்போது கிடைக்கவில்லை அல்லது கட்டமைக்கப்படவில்லை. சரிபார்க்கப்படாத சுருக்கத்தைத் தடுக்க "
            "உற்பத்தி ஃபால்பேக் முடக்கப்பட்டுள்ளது. தயவுசெய்து கீழே உள்ள அதிகாரப்பூர்வ வழிகாட்டுதல் சான்றுகளை மதிப்பாய்வு செய்யவும் "
            "அல்லது மருத்துவரை அணுகவும்."
        ),
        "hi": (
            "एआई चिकित्सीय सारांश अस्थायी रूप से अनुपलब्ध: प्राथमिक जेनेरेटिव चिकित्सीय सेवा (Google Gemini) "
            "वर्तमान में अनुपलब्ध या गैर-कॉन्फ़िगर है, और असत्यापित सारांश को रोकने के लिए प्रोडक्शन फ़ॉलबैक अक्षम है। "
            "कृपया नीचे दिए गए आधिकारिक दिशानिर्देश साक्ष्यों की समीक्षा करें या चिकित्सक से परामर्श करें।"
        ),
        "ml": (
            "എഐ ക്ലിനിക്കൽ സംഗ്രഹം താൽക്കാലികമായി ലഭ്യമല്ല: പ്രാഥമിക ജനറേറ്റീവ് ക്ലിനിക്കൽ ഇന്റലിജൻസ് സേവനം "
            "(Google Gemini) നിലവിൽ ലഭ്യമല്ല അല്ലെങ്കിൽ കോൺഫിഗർ ചെയ്തിട്ടില്ല. ഉൽപ്പാദന ഫാൾബാക്ക് അപ്രാപ്തമാക്കിയിരിക്കുന്നു. "
            "ദയവായി ചുവടെയുള്ള ആധികാരിക മാർഗ്ഗനിർദ്ദേശങ്ങൾ അവലോകനം ചെയ്യുക അല്ലെങ്കിൽ ഡോക്ടറെ സമീപിക്കുക."
        ),
        "te": (
            "AI క్లినికల్ సారాంశం తాత్కాలికంగా అందుబాటులో లేదు: ప్రాథమిక జనరేటివ్ క్లినికల్ ఇంటెలిజెన్స్ సేవ "
            "(Google Gemini) ప్రస్తుతం అందుబాటులో లేదు లేదా కాన్ఫిగర్ చేయబడలేదు. దయచేసి క్రింద ఉన్న అధికారిక మార్గదర్శకాలను సమీక్షించండి "
            "లేదా నమోదిత వైద్యుడిని సంప్రదించండి."
        ),
        "kn": (
            "AI ವೈದ್ಯಕೀಯ ಸಾರಾಂಶ ತಾತ್ಕಾಲಿಕವಾಗಿ ಲಭ್ಯವಿಲ್ಲ: ಪ್ರಾಥಮಿಕ ಕ್ಲಿನಿಕಲ್ ಇಂಟೆಲಿಜೆನ್ಸ್ ಸೇವೆ (Google Gemini) "
            "ಪ್ರಸ್ತುತ ಲಭ್ಯವಿಲ್ಲ ಅಥವಾ ಕಾನ್ಫಿಗರ್ ಮಾಡಲಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು ಕೆಳಗಿನ ಅಧಿಕೃತ ಮಾರ್ಗದರ್ಶನಗಳನ್ನು ಪರಿಶೀಲಿಸಿ ಅಥವಾ ನೋಂದಾಯಿತ ವೈದ್ಯರನ್ನು ಸಂಪರ್ಕಿಸಿ."
        ),
    }

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-1.5-flash",
        fallback_enabled: bool | None = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model
        self.fallback_enabled = (
            fallback_enabled if fallback_enabled is not None else settings.LLM_FALLBACK_ENABLED
        )
        self._fallback_provider = MockGroundedProvider()

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def is_available(self) -> bool:
        """Returns True if a non-empty API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def _build_citations(self, evidence: list[tuple[EvidenceChunk, float]]) -> list[Citation]:
        """Constructs structured Citation objects from retrieved evidence chunks."""
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
        return citations

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
    ) -> GroundedResponse:
        # 1. Abstention check if no evidence
        if not evidence or len(evidence) == 0:
            mock_res = self._fallback_provider.generate_grounded_response(
                query, evidence, language, emergency_detected
            )
            return GroundedResponse(
                answer=mock_res[0],
                citations=mock_res[1],
                abstained=mock_res[2],
                abstention_reason=mock_res[3],
                llm_provider="gemini",
                fallback_used=False,
                generation_mode="CONTROLLED_DEGRADED",
            )

        citations = self._build_citations(evidence)
        degraded_msg = self.MULTILINGUAL_DEGRADED_MESSAGES.get(
            language, self.MULTILINGUAL_DEGRADED_MESSAGES["en"]
        )

        # 2. Check API key presence
        if not self.is_available:
            if self.fallback_enabled:
                logger.info(
                    "GEMINI_API_KEY not configured. Executing mock fallback (LLM_FALLBACK_ENABLED=True)."
                )
                mock_res = self._fallback_provider.generate_grounded_response(
                    query, evidence, language, emergency_detected
                )
                return GroundedResponse(
                    answer=mock_res[0],
                    citations=mock_res[1],
                    abstained=mock_res[2],
                    abstention_reason=mock_res[3],
                    llm_provider="gemini",
                    fallback_used=True,
                    generation_mode="FALLBACK_MOCK",
                )
            else:
                logger.warning(
                    "GEMINI_API_KEY is not configured and LLM_FALLBACK_ENABLED=False. "
                    "Returning controlled degraded response."
                )
                return GroundedResponse(
                    answer=degraded_msg,
                    citations=citations,
                    abstained=True,
                    abstention_reason="GEMINI_API_KEY_MISSING",
                    llm_provider="gemini",
                    fallback_used=False,
                    generation_mode="CONTROLLED_DEGRADED",
                )

        # 3. Formulate prompt and call Gemini API
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
                            return GroundedResponse(
                                answer=sanitized,
                                citations=citations,
                                abstained=False,
                                abstention_reason=None,
                                llm_provider="gemini",
                                fallback_used=False,
                                generation_mode="GEMINI_DIRECT",
                            )

                logger.warning(
                    f"Gemini API returned non-200 status {res.status_code}: {res.text[:100]}."
                )
                error_reason = "GEMINI_API_ERROR"
        except Exception as exc:
            logger.warning(f"Gemini API invocation failed ({exc!s}).")
            error_reason = "GEMINI_NETWORK_UNAVAILABLE"

        # 4. Handle Gemini failure according to fallback configuration
        if self.fallback_enabled:
            logger.info("LLM_FALLBACK_ENABLED=True. Executing mock fallback after Gemini failure.")
            mock_res = self._fallback_provider.generate_grounded_response(
                query, evidence, language, emergency_detected
            )
            return GroundedResponse(
                answer=mock_res[0],
                citations=mock_res[1],
                abstained=mock_res[2],
                abstention_reason=mock_res[3],
                llm_provider="gemini",
                fallback_used=True,
                generation_mode="FALLBACK_MOCK",
            )
        else:
            logger.warning(
                "LLM_FALLBACK_ENABLED=False. Returning controlled degraded response due to Gemini failure."
            )
            return GroundedResponse(
                answer=degraded_msg,
                citations=citations,
                abstained=True,
                abstention_reason=error_reason,
                llm_provider="gemini",
                fallback_used=False,
                generation_mode="CONTROLLED_DEGRADED",
            )
