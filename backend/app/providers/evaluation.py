"""Reproducible evaluation harness for Doctor, Clinic & Hospital Discovery and Provider Verification."""

import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.providers.service import ProviderService


class ProviderEvaluationHarness:
    """Evaluates spatial accuracy, specialty filtering, verification tiers,

    provenance completeness, and emergency escalation against reference benchmark.
    """

    def __init__(self, benchmark_path: Path | str | None = None):
        self.benchmark_path = Path(
            benchmark_path or (Path(__file__).parent / "data" / "provider_evaluation_benchmark.json")
        )
        self.service = ProviderService()

    def load_benchmark(self) -> list[dict[str, Any]]:
        with open(self.benchmark_path, encoding="utf-8") as f:
            return json.load(f)

    async def run_evaluation(self, session: AsyncSession | None = None) -> dict[str, Any]:
        cases = self.load_benchmark()
        results: list[dict[str, Any]] = []

        # Category counters
        geo_total, geo_passed = 0, 0
        spec_total, spec_passed = 0, 0
        verif_total, verif_passed = 0, 0
        prov_total, prov_passed = 0, 0
        emerg_total, emerg_passed = 0, 0

        async def _eval_with_session(db: AsyncSession):
            nonlocal geo_total, geo_passed, spec_total, spec_passed
            nonlocal verif_total, verif_passed, prov_total, prov_passed
            nonlocal emerg_total, emerg_passed

            for case in cases:
                case_id = case["id"]
                category = case["category"]
                params = case["params"]
                expected = case["expected"]

                passed = True
                failures: list[str] = []

                # Execute search
                res = await self.service.search_providers(
                    db=db,
                    query=params.get("query"),
                    lat=params.get("lat"),
                    lon=params.get("lon"),
                    radius_km=params.get("radius_km", 10.0),
                    city=params.get("city"),
                    state=params.get("state"),
                    specialty=params.get("specialty"),
                    provider_type=params.get("provider_type", "all"),
                    verification_status=params.get("verification_status"),
                    open_now=params.get("open_now"),
                    page_size=params.get("page_size", 10),
                    language=params.get("language", "en"),
                )

                # Geographic checks
                if category == "geographic_proximity":
                    geo_total += 1
                    if "min_results" in expected and res.total < expected["min_results"]:
                        passed = False
                        failures.append(f"Expected >= {expected['min_results']} results, got {res.total}")
                    if "max_distance_km" in expected:
                        for it in res.items:
                            if it.distance_km is not None and it.distance_km > expected["max_distance_km"] + 0.1:
                                passed = False
                                failures.append(f"Distance {it.distance_km} exceeds {expected['max_distance_km']}km")
                    if expected.get("distance_sorted") and len(res.items) >= 2:
                        dists = [it.distance_km for it in res.items if it.distance_km is not None]
                        if dists != sorted(dists):
                            passed = False
                            failures.append("Items not sorted in ascending distance order")
                    if "city_matches" in expected:
                        for it in res.items:
                            if it.city != expected["city_matches"]:
                                passed = False
                                failures.append(f"City {it.city} does not match {expected['city_matches']}")
                    if passed:
                        geo_passed += 1

                # Specialty checks
                elif category == "specialty_filtering":
                    spec_total += 1
                    if "min_results" in expected and res.total < expected["min_results"]:
                        passed = False
                        failures.append(f"Expected >= {expected['min_results']} results, got {res.total}")
                    if "all_specialty_matches" in expected:
                        exp_spec = expected["all_specialty_matches"]
                        for it in res.items:
                            if it.card_type == "doctor" and it.specialty != exp_spec:
                                passed = False
                                failures.append(f"Doctor specialty {it.specialty} != {exp_spec}")
                    if passed:
                        spec_passed += 1

                # Verification checks
                elif category == "verification_status":
                    verif_total += 1
                    if "all_verification_status" in expected:
                        exp_v = expected["all_verification_status"]
                        for it in res.items:
                            if it.verification.status != exp_v:
                                passed = False
                                failures.append(f"Status {it.verification.status} != {exp_v}")
                    if "all_tiers" in expected:
                        exp_tier = expected["all_tiers"]
                        for it in res.items:
                            if it.verification.tier != exp_tier:
                                passed = False
                                failures.append(f"Tier {it.verification.tier} != {exp_tier}")
                    if expected.get("is_demo_labeled"):
                        for it in res.items:
                            if not it.verification.is_demo_data or not it.is_demo_data:
                                passed = False
                                failures.append("Missing explicit demo data flag")
                    if passed:
                        verif_passed += 1

                # Provenance checks
                elif category == "provenance_completeness":
                    prov_total += 1
                    for it in res.items:
                        v = it.verification
                        if not v.source or not v.method or not v.verified_at:
                            passed = False
                            failures.append(f"Item {it.id} missing provenance metadata")
                        if not v.is_demo_data or "DEMO" not in v.label:
                            passed = False
                            failures.append(f"Item {it.id} missing demo badge label")
                    if passed:
                        prov_passed += 1

                # Emergency checks
                elif category == "emergency_routing":
                    emerg_total += 1
                    esc = res.emergency_escalation
                    if expected.get("emergency_escalation_triggered"):
                        if not esc or not esc.is_emergency:
                            passed = False
                            failures.append("Expected emergency escalation but none triggered")
                        elif esc.level != expected.get("emergency_level", "CRITICAL"):
                            passed = False
                            failures.append(f"Level {esc.level} != {expected.get('emergency_level')}")
                        if expected.get("contains_helpline_112") and "112" not in (esc.emergency_numbers if esc else []):
                            passed = False
                            failures.append("Emergency numbers missing 112")
                    if passed:
                        emerg_passed += 1

                # Edge cases
                elif category == "edge_case":
                    if "exact_total" in expected and res.total != expected["exact_total"]:
                        passed = False
                        failures.append(f"Total {res.total} != {expected['exact_total']}")
                    if expected.get("empty_items") and len(res.items) != 0:
                        passed = False
                        failures.append(f"Items length {len(res.items)} != 0")
                    if "all_card_types" in expected:
                        for it in res.items:
                            if it.card_type != expected["all_card_types"]:
                                passed = False
                                failures.append(f"Card type {it.card_type} != {expected['all_card_types']}")

                results.append({
                    "id": case_id,
                    "category": category,
                    "description": case["description"],
                    "passed": passed,
                    "failures": failures,
                    "results_count": res.total,
                })

        if session:
            await _eval_with_session(session)
        else:
            async with AsyncSessionLocal() as db:
                await _eval_with_session(db)

        # Compute metric percentages
        geo_metric = (geo_passed / geo_total * 100.0) if geo_total else 100.0
        spec_metric = (spec_passed / spec_total * 100.0) if spec_total else 100.0
        verif_metric = (verif_passed / verif_total * 100.0) if verif_total else 100.0
        prov_metric = (prov_passed / prov_total * 100.0) if prov_total else 100.0
        emerg_metric = (emerg_passed / emerg_total * 100.0) if emerg_total else 100.0

        all_passed = all(r["passed"] for r in results)

        return {
            "total_cases": len(cases),
            "passed_cases": sum(1 for r in results if r["passed"]),
            "overall_pass": all_passed,
            "metrics": {
                "geographic_search_correctness": round(geo_metric, 2),
                "specialty_filtering_correctness": round(spec_metric, 2),
                "verification_status_correctness": round(verif_metric, 2),
                "provenance_completeness": round(prov_metric, 2),
                "emergency_routing_correctness": round(emerg_metric, 2),
            },
            "category_counts": {
                "geographic": f"{geo_passed}/{geo_total}",
                "specialty": f"{spec_passed}/{spec_total}",
                "verification": f"{verif_passed}/{verif_total}",
                "provenance": f"{prov_passed}/{prov_total}",
                "emergency": f"{emerg_passed}/{emerg_total}",
            },
            "dataset_limitation_statement": (
                "Evaluation evaluated over 15-case internal reference benchmark against canonical "
                "seeded PostGIS providers dataset. Real-world accuracy will depend on jurisdictional "
                "medical registry APIs (NMC, NABH) and live reverse-geocoding limits."
            ),
            "results": results,
        }
