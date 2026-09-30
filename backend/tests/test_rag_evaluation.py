"""Pytest execution wrapper for RAG evaluation harness benchmark."""

import pytest

from app.rag.evaluation import RAGEvaluationHarness


@pytest.mark.asyncio
async def test_rag_evaluation_benchmark_all_cases():
    harness = RAGEvaluationHarness()
    report = await harness.run_evaluation()

    assert report["overall_pass"] is True, f"Failed cases: {[r for r in report['results'] if not r['passed']]}"
    assert report["retrieval_accuracy"] == 100.0
    assert report["abstention_rate"] == 100.0
    assert report["emergency_detection_rate"] == 100.0
    assert report["multilingual_retrieval_rate"] == 100.0
    assert report["prompt_injection_defense_rate"] == 100.0
