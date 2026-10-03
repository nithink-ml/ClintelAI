"""Base interface for Clinical LLM Providers."""

from abc import ABC, abstractmethod

from app.rag.models import Citation, EvidenceChunk


class BaseLLMProvider(ABC):
    """Abstract Base Class for grounded clinical LLM providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the name identifier for this provider."""

    @abstractmethod
    def generate_grounded_response(
        self,
        query: str,
        evidence: list[tuple[EvidenceChunk, float]],
        language: str = "en",
        emergency_detected: bool = False,
    ) -> tuple[str, list[Citation], bool, str | None]:
        """Synthesizes an evidence-grounded response with explicit inline citations.

        Returns:
            (answer_text, citations_list, abstained_bool, abstention_reason)
        """
