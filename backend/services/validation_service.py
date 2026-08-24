"""
India Climate Digital Twin
Scientific Validation Service

Validates the rainfall-based climate risk engine against
the scientific consistency conditions used by the project.
"""

from __future__ import annotations

from collections import Counter

from backend.services.climate_risk_service import (
    get_climate_risk_grid,
)

VALIDATION_DATE = "2024-07-15"

HEAVY_THRESHOLD = 64.5
VERY_HEAVY_THRESHOLD = 115.6
EXTREMELY_HEAVY_THRESHOLD = 204.5


def run_validation() -> None:

    print("=" * 70)
    print("INDIA CLIMATE DIGITAL TWIN")
    print("SCIENTIFIC VALIDATION")
    print("=" * 70)

    print()
    print(f"Date: {VALIDATION_DATE}")

    # ---------------------------------------------------------
    # LOAD RISK GRID
    # ---------------------------------------------------------

    result = get_climate_risk_grid(
        VALIDATION_DATE
    )

    features = result["features"]

    print()
    print("-" * 70)
    print("GRID VALIDATION")
    print("-" * 70)

    print(
        f"Valid features: {len(features)}"
    )

    assert len(features) > 0, (
        "Risk grid contains no valid features."
    )

    # ---------------------------------------------------------
    # RISK DISTRIBUTION
    # ---------------------------------------------------------

    categories = Counter(
        feature["properties"]["risk_category"]
        for feature in features
    )

    print()
    print("-" * 70)
    print("RISK DISTRIBUTION")
    print("-" * 70)

    for category in (
        "low",
        "moderate",
        "high",
        "extreme",
    ):

        print(
            f"{category.capitalize():10}: "
            f"{categories.get(category, 0)}"
        )

    total_categories = sum(
        categories.values()
    )

    assert total_categories == len(features), (
        "Risk categories do not account for "
        "all valid grid features."
    )

    print(
        "Category total consistency: PASS"
    )

    # =========================================================
    # REQUIRED PROPERTY VALIDATION
    # =========================================================

    print()
    print("-" * 70)
    print("PROPERTY VALIDATION")
    print("-" * 70)

    required_properties = {
        "date",
        "rainfall_mm",
        "hazard_score",
        "risk_category",
        "rainfall_category",
    }

    for feature in features:

        properties = feature["properties"]

        missing = (
            required_properties
            - set(properties.keys())
        )

        assert not missing, (
            f"Missing properties: {missing}"
        )

    print(
        "Required properties: PASS"
    )

    # =========================================================
    # RAINFALL VALIDATION
    # =========================================================

    rainfall_values = [
        float(
            feature["properties"]["rainfall_mm"]
        )
        for feature in features
    ]

    maximum_rainfall = max(
        rainfall_values
    )

    maximum_feature = max(
        features,
        key=lambda feature:
            float(
                feature["properties"]
                ["rainfall_mm"]
            )
    )

    maximum_properties = (
        maximum_feature["properties"]
    )

    print()
    print("-" * 70)
    print("MAXIMUM RAINFALL VALIDATION")
    print("-" * 70)

    print(
        f"Maximum rainfall: "
        f"{maximum_rainfall:.2f} mm"
    )

    coordinates = (
        maximum_feature["geometry"]
        ["coordinates"]
    )

    print(
        f"Longitude: {coordinates[0]}"
    )

    print(
        f"Latitude: {coordinates[1]}"
    )

    print(
        f"Hazard score: "
        f"{maximum_properties['hazard_score']}"
    )

    print(
        f"Risk category: "
        f"{maximum_properties['risk_category']}"
    )

    print(
        f"Rainfall category: "
        f"{maximum_properties['rainfall_category']}"
    )

    # =========================================================
    # RAINFALL THRESHOLD VALIDATION
    # =========================================================

    print()
    print("-" * 70)
    print("THRESHOLD VALIDATION")
    print("-" * 70)

    for feature in features:

        properties = feature["properties"]

        rainfall = float(
            properties["rainfall_mm"]
        )

        rainfall_category = (
            properties["rainfall_category"]
        )

        if rainfall >= EXTREMELY_HEAVY_THRESHOLD:

            assert rainfall_category == (
                "extremely_heavy"
            ), (
                f"Expected extremely_heavy "
                f"for {rainfall} mm, "
                f"got {rainfall_category}"
            )

        elif rainfall >= VERY_HEAVY_THRESHOLD:

            assert rainfall_category == (
                "very_heavy"
            ), (
                f"Expected very_heavy "
                f"for {rainfall} mm, "
                f"got {rainfall_category}"
            )

        elif rainfall >= HEAVY_THRESHOLD:

            assert rainfall_category == (
                "heavy"
            ), (
                f"Expected heavy "
                f"for {rainfall} mm, "
                f"got {rainfall_category}"
            )

    print(
        "IMD rainfall thresholds: PASS"
    )

    # ---------------------------------------------------------
    # HAZARD SCORE VALIDATION
    # ---------------------------------------------------------

    print()
    print("-" * 70)
    print("HAZARD SCORE VALIDATION")
    print("-" * 70)

    for feature in features:

        score = float(
            feature["properties"]["hazard_score"]
        )

        assert 0 <= score <= 100, (
            f"Invalid hazard score: {score}"
        )

    print(
        "Score range 0-100: PASS"
    )

    # =========================================================
    # EXTREME RISK VALIDATION
    # =========================================================

    extreme_features = [
        feature
        for feature in features
        if feature["properties"]
        ["risk_category"]
        == "extreme"
    ]

    print()
    print("-" * 70)
    print("EXTREME RISK VALIDATION")
    print("-" * 70)

    print(
        f"Extreme risk points: "
        f"{len(extreme_features)}"
    )

    for feature in extreme_features:

        rainfall = float(
            feature["properties"]["rainfall_mm"]
        )

        assert rainfall >= (
            EXTREMELY_HEAVY_THRESHOLD
        ), (
            "Extreme risk point does not "
            "meet the extremely-heavy "
            "rainfall threshold."
        )

    print(
        "Extreme-risk threshold consistency: PASS"
    )

    # =========================================================
    # MAXIMUM POINT CONSISTENCY
    # =========================================================

    print()
    print("-" * 70)
    print("MAXIMUM POINT CONSISTENCY")
    print("-" * 70)

    assert (
        maximum_properties["risk_category"]
        == "extreme"
    ), (
        "Maximum rainfall point is not "
        "classified as extreme risk."
    )

    assert (
        maximum_rainfall
        >= EXTREMELY_HEAVY_THRESHOLD
    ), (
        "Maximum rainfall does not meet "
        "the extremely-heavy threshold."
    )

    print(
        "Maximum point risk consistency: PASS"
    )

    # ---------------------------------------------------------
    # FINAL RESULT
    # ---------------------------------------------------------

    print()
    print("=" * 70)
    print("SCIENTIFIC VALIDATION COMPLETE")
    print("ALL CHECKS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    run_validation()
