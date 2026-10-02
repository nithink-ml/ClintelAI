"""Pytest test wrapper executing the Phase 3 Provider Evaluation Benchmark."""

import pytest

from app.providers.evaluation import ProviderEvaluationHarness


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_provider_evaluation_benchmark_all_cases():
    """Runs the 15-case benchmark and validates 100% metrics across all criteria."""
    harness = ProviderEvaluationHarness()
    report = await harness.run_evaluation()

    failures = [r for r in report["results"] if not r["passed"]]
    assert report["overall_pass"] is True, f"Failed evaluation cases: {failures}"
    assert report["total_cases"] == 15
    assert report["passed_cases"] == 15

    metrics = report["metrics"]
    assert metrics["geographic_search_correctness"] == 100.0
    assert metrics["specialty_filtering_correctness"] == 100.0
    assert metrics["verification_status_correctness"] == 100.0
    assert metrics["provenance_completeness"] == 100.0
    assert metrics["emergency_routing_correctness"] == 100.0
