"""Pytest Global Test Fixtures and Deterministic Environment Configuration."""

import pytest

from app.core.config import settings
from app.rag.providers.factory import _CACHED_PROVIDERS


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    """Enforces deterministic offline execution for the general test suite.

    - Uses MockGroundedProvider for deterministic RAG tests and benchmarks.
    - Tests specifically validating GeminiProvider explicitly instantiate or configure it.
    - Clears provider singleton cache between tests.
    """
    monkeypatch.setattr(settings, "LLM_PROVIDER", "mock")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    _CACHED_PROVIDERS.clear()
    yield
    _CACHED_PROVIDERS.clear()
