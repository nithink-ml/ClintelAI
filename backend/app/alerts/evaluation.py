"""Reproducible evaluation harness for Regional Health Alerts, Multilingual Ingestion, and Spatial Routing."""

import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.alerts.service import HealthAlertService
from app.db.session import AsyncSessionLocal


class HealthAlertEvaluationHarness:
    """Evaluates spatial matching, category/severity filtering, status lifecycle,
    multilingual delivery, provenance, and emergency red-flag interception.
    """

    def __init__(self, benchmark_path: Path | str | None = None):
        self.benchmark_path = Path(
            benchmark_path or (Path(__file__).parent / "data" / "alert_evaluation_benchmark.json")
        )
        self.service = HealthAlertService()

    def load_benchmark(self) -> list[dict[str, Any]]:
        with open(self.benchmark_path, encoding="utf-8") as f:
            return json.load(f)

    async def run_evaluation(self, session: AsyncSession | None = None) -> dict[str, Any]:
        cases = self.load_benchmark()
        results: list[dict[str, Any]] = []

        # Category counters
        geo_total, geo_passed = 0, 0
        nat_total, nat_passed = 0, 0
        cat_total, cat_passed = 0, 0
        sev_total, sev_passed = 0, 0
        stat_total, stat_passed = 0, 0
        lang_total, lang_passed = 0, 0
        emerg_total, emerg_passed = 0, 0
        prov_total, prov_passed = 0, 0

        async def _eval_with_session(db: AsyncSession):
            nonlocal geo_total, geo_passed, nat_total, nat_passed
            nonlocal cat_total, cat_passed, sev_total, sev_passed
            nonlocal stat_total, stat_passed, lang_total, lang_passed
            nonlocal emerg_total, emerg_passed, prov_total, prov_passed

            for case in cases:
                case_id = case["id"]
                category = case["category"]
                params = case["params"]
                expected = case["expected"]

                passed = True
                failures: list[str] = []

                # Execute alert search
                res = await self.service.search_alerts(
                    db=db,
                    query=params.get("query"),
                    lat=params.get("lat"),
                    lon=params.get("lon"),
                    state=params.get("state"),
                    district=params.get("district"),
                    city=params.get("city"),
                    category=params.get("category"),
                    severity=params.get("severity"),
                    status=params.get("status"),
                    language=params.get("language", "en"),
                    page=params.get("page", 1),
                    page_size=params.get("page_size", 10),
                )

                # Min results check
                if "min_results" in expected and res.total < expected["min_results"]:
                    passed = False
                    failures.append(f"Expected at least {expected['min_results']} results, got {res.total}")

                # Contains title check
                if "contains_title" in expected:
                    needle = expected["contains_title"].lower()
                    found = any(needle in item.title.lower() or needle in item.summary.lower() for item in res.items)
                    if not found:
                        passed = False
                        failures.append(f"Expected results to contain title keyword '{expected['contains_title']}'")

                # Contains national scope alert
                if expected.get("contains_national"):
                    has_nat = any(item.state is None or (item.state and item.state.upper() == "ALL_INDIA") for item in res.items)
                    if not has_nat:
                        passed = False
                        failures.append("Expected results to include national scope (ALL_INDIA) alert")

                # Category matching
                if "all_category_match" in expected:
                    target_cat = expected["all_category_match"].lower()
                    mismatched = [item.title for item in res.items if item.category.lower() != target_cat]
                    if mismatched:
                        passed = False
                        failures.append(f"Expected all items to match category '{target_cat}', but found: {mismatched}")

                # Severity matching
                if "all_severity_match" in expected:
                    target_sev = expected["all_severity_match"].upper()
                    mismatched = [item.title for item in res.items if item.severity.upper() != target_sev]
                    if mismatched:
                        passed = False
                        failures.append(f"Expected all items to match severity '{target_sev}', but found: {mismatched}")

                # Status matching
                if "all_status_match" in expected:
                    target_stat = expected["all_status_match"].upper()
                    mismatched = [item.title for item in res.items if item.status.upper() != target_stat]
                    if mismatched:
                        passed = False
                        failures.append(f"Expected all items to match status '{target_stat}', but found: {mismatched}")

                # Excludes title keyword
                if "excludes_title" in expected:
                    bad_needle = expected["excludes_title"].lower()
                    found_bad = any(bad_needle in item.title.lower() for item in res.items)
                    if found_bad:
                        passed = False
                        failures.append(f"Found forbidden title keyword '{expected['excludes_title']}' in results")

                # Tamil translation check
                if expected.get("contains_tamil_title"):
                    # Check for Tamil characters in titles (Unicode range 0B80–0BFF)
                    has_tamil = any(any("\u0b80" <= char <= "\u0bff" for char in item.title) for item in res.items)
                    if not has_tamil:
                        passed = False
                        failures.append("Expected at least one alert to have localized Tamil script in title")

                # Emergency escalation check
                if expected.get("emergency_triggered"):
                    if not res.emergency_escalation or not res.emergency_escalation.is_emergency:
                        passed = False
                        failures.append("Expected emergency escalation to trigger, but was None or False")
                    else:
                        if expected.get("emergency_level") and res.emergency_escalation.level != expected["emergency_level"]:
                            passed = False
                            failures.append(
                                f"Expected emergency urgency '{expected['emergency_level']}', got '{res.emergency_escalation.level}'"
                            )
                        if expected.get("contains_112"):
                            helplines = res.emergency_escalation.emergency_numbers or []
                            if "112" not in helplines and not any("112" in str(h) for h in helplines):
                                passed = False
                                failures.append("Expected national emergency helpline '112' in escalation helplines")

                # Provenance and demo guardrails
                if expected.get("provenance_complete"):
                    missing_source = [item.title for item in res.items if not item.source_name or not item.source_url]
                    if missing_source:
                        passed = False
                        failures.append(f"Missing source metadata for: {missing_source}")

                if expected.get("all_demo_flagged"):
                    unflagged = [item.title for item in res.items if item.is_demo_data is not True]
                    if unflagged:
                        passed = False
                        failures.append(f"Alerts missing is_demo_data=True guardrail flag: {unflagged}")

                if expected.get("freshness_computed"):
                    bad_freshness = [item.title for item in res.items if not item.freshness or not item.freshness.status]
                    if bad_freshness:
                        passed = False
                        failures.append(f"Missing freshness status evaluation for: {bad_freshness}")

                # Update Category Stats
                if category == "geographic_matching":
                    geo_total += 1
                    if passed:
                        geo_passed += 1
                elif category == "national_propagation":
                    nat_total += 1
                    if passed:
                        nat_passed += 1
                elif category == "category_filtering":
                    cat_total += 1
                    if passed:
                        cat_passed += 1
                elif category == "severity_filtering":
                    sev_total += 1
                    if passed:
                        sev_passed += 1
                elif category == "status_lifecycle":
                    stat_total += 1
                    if passed:
                        stat_passed += 1
                elif category == "multilingual_fidelity":
                    lang_total += 1
                    if passed:
                        lang_passed += 1
                elif category == "emergency_routing":
                    emerg_total += 1
                    if passed:
                        emerg_passed += 1
                elif category == "provenance_and_guardrail":
                    prov_total += 1
                    if passed:
                        prov_passed += 1

                results.append({
                    "id": case_id,
                    "category": category,
                    "description": case["description"],
                    "passed": passed,
                    "failures": failures,
                    "result_count": res.total,
                })

        if session:
            await _eval_with_session(session)
        else:
            async with AsyncSessionLocal() as db:
                await _eval_with_session(db)

        total_cases = len(cases)
        passed_cases = sum(1 for r in results if r["passed"])

        def calc_pct(p: int, t: int) -> float:
            return round((p / t * 100.0) if t > 0 else 100.0, 1)

        metrics = {
            "geographic_search_correctness": calc_pct(geo_passed, geo_total),
            "national_propagation_correctness": calc_pct(nat_passed, nat_total),
            "category_filtering_correctness": calc_pct(cat_passed, cat_total),
            "severity_filtering_correctness": calc_pct(sev_passed, sev_total),
            "status_lifecycle_correctness": calc_pct(stat_passed, stat_total),
            "multilingual_fidelity_correctness": calc_pct(lang_passed, lang_total),
            "emergency_routing_correctness": calc_pct(emerg_passed, emerg_total),
            "provenance_and_guardrail_correctness": calc_pct(prov_passed, prov_total),
            "overall_accuracy": calc_pct(passed_cases, total_cases),
        }

        return {
            "total_cases": total_cases,
            "passed_cases": passed_cases,
            "overall_pass": (passed_cases == total_cases),
            "metrics": metrics,
            "results": results,
        }
