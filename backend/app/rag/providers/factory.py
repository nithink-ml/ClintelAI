"""Factory for instantiating clinical LLM providers."""

from app.core.config import settings
from app.rag.providers.base import BaseLLMProvider
from app.rag.providers.gemini import GeminiProvider
from app.rag.providers.mock import MockGroundedProvider

_CACHED_PROVIDERS: dict[str, BaseLLMProvider] = {}


def get_llm_provider(name: str | None = None) -> BaseLLMProvider:
    """Returns the configured LLM provider singleton instance.

    Supported options:
    - 'mock': Deterministic, offline-safe evidence-grounded generator
    - 'gemini': Google Gemini generative model with strict prompt grounding
    """
    provider_name = (name or settings.LLM_PROVIDER).lower()

    if provider_name not in _CACHED_PROVIDERS:
        if provider_name == "gemini":
            _CACHED_PROVIDERS[provider_name] = GeminiProvider()
        else:
            _CACHED_PROVIDERS[provider_name] = MockGroundedProvider()

    return _CACHED_PROVIDERS[provider_name]
