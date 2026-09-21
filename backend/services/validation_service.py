"""Scientific consistency validation for the rainfall hazard engine.

The checks here verify internal consistency of the implemented rainfall
components: category thresholds, score range, and the relationship between
extreme-risk points and the extremely-heavy rainfall threshold. They are
consistency checks, not accuracy validation against an independent reference.

Results are returned as structured data so they can back an API endpoint and
be asserted in tests; ``run_validation`` remains the human-readable CLI entry
point.
"""
from __future__ import annotations

from collections import Counter
from typing import Any

from backend.services.climate_risk_service import (
    EXTREMELY_HEAVY_THRESHOLD_MM,
    HEAVY_THRESHOLD_MM,
    VERY_HEAVY_THRESHOLD_MM,
    get_climate_risk_grid,
)

VALIDATION_DATE = "2024-07-15"

THRESHOLDS = (
    ("extremely_heavy", EXTREMELY_HEAVY_THRESHOLD_MM),
    ("very_heavy", VERY_HEAVY_THRESHOLD_MM),
    ("heavy", HEAVY_THRESHOLD_MM),
)

REQUIRED_PROPERTIES = {
    "date",
    "rainfall_mm",
    "hazard_score",
    "risk_category",
    "rainfall_category",
}


def _expected_category(rainfall_mm: float) -> str:
    for name, threshold in THRESHOLDS:
        if rainfall_mm >= threshold:
            return name
    return "no_event"


def validate_risk_grid(date: str = VALIDATION_DATE) -> dict[str, Any]:
    """Run every consistency check and return a structured report.

    Each check is recorded with ``passed`` and, when it fails, the offending
    detail. A failing check is reported rather than raised so the endpoint
    returns a complete picture instead of only the first problem.
    """
    result = get_climate_risk_grid(date)
    features = result.get("features", [])
    checks: list[dict[str, Any]] = []

    def record(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    record("grid_has_features", len(features) > 0, f"feature_count={len(features)}")
    if not features:
        return _report(date, checks, None)

    properties = [feature.get("properties", {}) for feature in features]

    missing = sorted({key for props in properties for key in REQUIRED_PROPERTIES - set(props)})
    record("required_properties_present", not missing, f"missing={missing}")

    rainfall_values = [float(props["rainfall_mm"]) for props in properties]
    scores = [float(props["hazard_score"]) for props in properties]
    categories = Counter(props["risk_category"] for props in properties)

    maximum_rainfall = max(rainfall_values)
    maximum_index = rainfall_values.index(maximum_rainfall)
    maximum_properties = properties[maximum_index]
    maximum_geometry = features[maximum_index].get("geometry", {}).get("coordinates", [None, None])

    record(
        "risk_categories_account_for_all_features",
        sum(categories.values()) == len(features),
        f"categorised={sum(categories.values())} features={len(features)}",
    )
    record(
        "hazard_score_within_range",
        all(0.0 <= score <= 100.0 for score in scores),
        f"score_range=({min(scores):.2f},{max(scores):.2f})",
    )

    mismatches = [
        {"rainfall_mm": rainfall, "expected": _expected_category(rainfall), "actual": props["rainfall_category"]}
        for rainfall, props in zip(rainfall_values, properties)
        if props["rainfall_category"] != _expected_category(rainfall)
    ]
    record(
        "rainfall_categories_match_imd_thresholds",
        not mismatches,
        f"mismatch_count={len(mismatches)} first={mismatches[0] if mismatches else None}",
    )

    extreme_properties = [props for props in properties if props["risk_category"] == "extreme"]
    extreme_violations = [
        props["rainfall_mm"]
        for props in extreme_properties
        if float(props["rainfall_mm"]) < EXTREMELY_HEAVY_THRESHOLD_MM
    ]
    record(
        "extreme_risk_points_meet_extremely_heavy_threshold",
        not extreme_violations,
        f"violations={extreme_violations[:5]}",
    )

    record(
        "maximum_rainfall_point_is_extreme_risk",
        maximum_properties["risk_category"] == "extreme"
        and maximum_rainfall >= EXTREMELY_HEAVY_THRESHOLD_MM,
        f"maximum_rainfall_mm={maximum_rainfall:.2f} category={maximum_properties['risk_category']}",
    )

    summary = {
        "valid_features": len(features),
        "risk_distribution": dict(categories),
        "maximum_rainfall_mm": maximum_rainfall,
        "maximum_point": {
            "longitude": maximum_geometry[0],
            "latitude": maximum_geometry[1],
            "hazard_score": maximum_properties.get("hazard_score"),
            "risk_category": maximum_properties.get("risk_category"),
            "rainfall_category": maximum_properties.get("rainfall_category"),
        },
    }
    return _report(date, checks, summary)


def _report(date, checks, summary) -> dict[str, Any]:
    passed = sum(1 for check in checks if check["passed"])
    return {
        "date": date,
        "validation_type": "internal_consistency",
        "scope": "rainfall hazard engine over the IMD 0.25-degree grid",
        "status": "passed" if checks and passed == len(checks) else "failed",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
        "summary": summary,
        "limitations": [
            "Consistency validation only; no independent observational reference is used.",
            "Risk engine has not been calibrated against an operational flood or heat-health model.",
        ],
    }


def run_validation() -> dict[str, Any]:
    report = validate_risk_grid()
    print("=" * 70)
    print("INDIA CLIMATE DIGITAL TWIN")
    print("SCIENTIFIC VALIDATION")
    print("=" * 70)
    for check in report["checks"]:
        print(f"[{'PASS' if check['passed'] else 'FAIL'}] {check['check']} :: {check['detail']}")
    print(f"\nOverall: {report['status']} ({report['checks_passed']}/{report['checks_total']})")
    return report


if __name__ == "__main__":
    run_validation()
