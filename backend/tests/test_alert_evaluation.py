"""Pytest test wrapper executing the Phase 4 Regional Health Alerts Evaluation Benchmark."""

import pytest

from app.alerts.evaluation import HealthAlertEvaluationHarness


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health_alert_evaluation_benchmark_all_cases():
    """Runs the 15-case benchmark and validates 100% metrics across all criteria."""
    harness = HealthAlertEvaluationHarness()
    report = await harness.run_evaluation()

    failures = [r for r in report["results"] if not r["passed"]]
    assert report["overall_pass"] is True, f"Failed evaluation cases: {failures}"
    assert report["total_cases"] == 15
    assert report["passed_cases"] == 15

    metrics = report["metrics"]
    assert metrics["geographic_search_correctness"] == 100.0
    assert metrics["national_propagation_correctness"] == 100.0
    assert metrics["category_filtering_correctness"] == 100.0
    assert metrics["severity_filtering_correctness"] == 100.0
    assert metrics["status_lifecycle_correctness"] == 100.0
    assert metrics["multilingual_fidelity_correctness"] == 100.0
    assert metrics["emergency_routing_correctness"] == 100.0
    assert metrics["provenance_and_guardrail_correctness"] == 100.0
    assert metrics["overall_accuracy"] == 100.0
