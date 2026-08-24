from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr


# ============================================================
# CONFIGURATION
# ============================================================

DATA_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "RF25_ind2024_rfp25.nc"
)


# ============================================================
# IMD RAINFALL THRESHOLDS
# ============================================================

HEAVY_THRESHOLD_MM = 64.5

VERY_HEAVY_THRESHOLD_MM = 115.6

EXTREMELY_HEAVY_THRESHOLD_MM = 204.5


# ============================================================
# RISK SCORE LIMITS
# ============================================================

LOW_MAX_SCORE = 24.99

MODERATE_MAX_SCORE = 49.99

HIGH_MAX_SCORE = 74.99

EXTREME_MAX_SCORE = 100.0


# ============================================================
# DATASET
# ============================================================

def load_dataset() -> xr.Dataset:
    """
    Open the IMD rainfall NetCDF dataset.
    """

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Rainfall dataset not found: {DATA_FILE}"
        )

    return xr.open_dataset(DATA_FILE)


# ============================================================
# DATE VALIDATION
# ============================================================

def validate_date(
    dataset: xr.Dataset,
    date: str,
) -> xr.DataArray:
    """
    Validate and return rainfall data for a date.
    """

    try:

        return dataset["RAINFALL"].sel(
            TIME=date
        )

    except Exception as error:

        raise ValueError(
            f"Invalid or unavailable date '{date}'. "
            f"Dataset covers "
            f"{str(dataset['TIME'].min().values)} "
            f"to "
            f"{str(dataset['TIME'].max().values)}."
        ) from error


# ============================================================
# CLEAN VALUES
# ============================================================

def clean_rainfall_values(
    values: Any,
) -> np.ndarray:
    """
    Convert rainfall values to float32
    and remove invalid values.
    """

    values = np.asarray(
        values,
        dtype=np.float32,
    )

    values[
        ~np.isfinite(values)
    ] = np.nan

    values[
        np.abs(values) > 10000
    ] = np.nan

    return values


# ============================================================
# RAINFALL CATEGORY
# ============================================================

def classify_rainfall(
    rainfall_mm: float,
) -> str:
    """
    Classify rainfall intensity.

    Categories:

        no_event
        heavy
        very_heavy
        extremely_heavy
    """

    if not np.isfinite(rainfall_mm):
        return "no_data"

    if rainfall_mm >= EXTREMELY_HEAVY_THRESHOLD_MM:
        return "extremely_heavy"

    if rainfall_mm >= VERY_HEAVY_THRESHOLD_MM:
        return "very_heavy"

    if rainfall_mm >= HEAVY_THRESHOLD_MM:
        return "heavy"

    return "no_event"


# ============================================================
# CONTINUOUS RISK SCORE
# ============================================================

def calculate_risk_score(
    rainfall_mm: float,
) -> float:
    """
    Calculate a rainfall hazard score from 0 to 100.

    The score is continuous within each rainfall
    intensity interval.

    Interpretation:

        < 64.5 mm
            0 - 24.99

        64.5 - 115.5 mm
            25 - 49.99

        115.6 - 204.4 mm
            50 - 74.99

        >= 204.5 mm
            75 - 100
    """

    if not np.isfinite(rainfall_mm):
        return float("nan")

    # --------------------------------------------------------
    # LOW / NORMAL
    # --------------------------------------------------------

    if rainfall_mm < HEAVY_THRESHOLD_MM:

        # Map 0 -> 0 and 64.5 -> 24.99.
        score = (
            rainfall_mm
            / HEAVY_THRESHOLD_MM
        ) * LOW_MAX_SCORE

        return float(
            np.clip(
                score,
                0.0,
                LOW_MAX_SCORE,
            )
        )

    # --------------------------------------------------------
    # HEAVY
    # --------------------------------------------------------

    if rainfall_mm < VERY_HEAVY_THRESHOLD_MM:

        lower = HEAVY_THRESHOLD_MM

        upper = VERY_HEAVY_THRESHOLD_MM

        normalized = (
            rainfall_mm - lower
        ) / (
            upper - lower
        )

        score = (
            25.0
            + normalized * 24.99
        )

        return float(
            np.clip(
                score,
                25.0,
                MODERATE_MAX_SCORE,
            )
        )

    # --------------------------------------------------------
    # VERY HEAVY
    # --------------------------------------------------------

    if rainfall_mm < EXTREMELY_HEAVY_THRESHOLD_MM:

        lower = VERY_HEAVY_THRESHOLD_MM

        upper = EXTREMELY_HEAVY_THRESHOLD_MM

        normalized = (
            rainfall_mm - lower
        ) / (
            upper - lower
        )

        score = (
            50.0
            + normalized * 24.99
        )

        return float(
            np.clip(
                score,
                50.0,
                HIGH_MAX_SCORE,
            )
        )

    # --------------------------------------------------------
    # EXTREMELY HEAVY
    # --------------------------------------------------------

    # 204.5 mm = 75
    #
    # Score approaches 100 as rainfall increases.
    #
    # 404.5 mm or above = 100.

    score = (
        75.0
        + (
            (
                rainfall_mm
                - EXTREMELY_HEAVY_THRESHOLD_MM
            )
            / 200.0
        ) * 25.0
    )

    return float(
        np.clip(
            score,
            75.0,
            EXTREME_MAX_SCORE,
        )
    )


# ============================================================
# RISK CATEGORY
# ============================================================

def classify_risk_score(
    score: float,
) -> str:
    """
    Convert a 0-100 risk score into a category.
    """

    if not np.isfinite(score):
        return "no_data"

    if score < 25.0:
        return "low"

    if score < 50.0:
        return "moderate"

    if score < 75.0:
        return "high"

    return "extreme"


# ============================================================
# SINGLE POINT RISK
# ============================================================

def calculate_point_risk(
    rainfall_mm: float,
) -> dict[str, Any]:
    """
    Calculate rainfall risk information
    for one grid point.
    """

    if not np.isfinite(rainfall_mm):

        return {
            "rainfall_mm": None,
            "hazard_score": None,
            "risk_category": "no_data",
            "rainfall_category": "no_data",
        }

    score = calculate_risk_score(
        rainfall_mm
    )

    return {
        "rainfall_mm": float(
            rainfall_mm
        ),

        "hazard_score": round(
            score,
            2,
        ),

        "risk_category":
            classify_risk_score(score),

        "rainfall_category":
            classify_rainfall(
                rainfall_mm
            ),
    }


# ============================================================
# SPATIAL RISK GRID
# ============================================================

def get_climate_risk_grid(
    date: str,
) -> dict[str, Any]:
    """
    Calculate rainfall hazard risk
    for every valid grid point.

    Returns a GeoJSON FeatureCollection.
    """

    dataset = load_dataset()

    try:

        selected = validate_date(
            dataset,
            date,
        )

        values = clean_rainfall_values(
            selected.values
        )

        latitudes = np.asarray(
            dataset["LATITUDE"].values,
            dtype=float,
        )

        longitudes = np.asarray(
            dataset["LONGITUDE"].values,
            dtype=float,
        )

        features = []

        risk_counts = {
            "low": 0,
            "moderate": 0,
            "high": 0,
            "extreme": 0,
            "no_data": 0,
        }

        hazard_scores = []

        maximum_risk = None

        # ----------------------------------------------------
        # PROCESS EVERY GRID POINT
        # ----------------------------------------------------

        for lat_index, latitude in enumerate(
            latitudes
        ):

            for lon_index, longitude in enumerate(
                longitudes
            ):

                rainfall_value = float(
                    values[
                        lat_index,
                        lon_index,
                    ]
                )

                point = calculate_point_risk(
                    rainfall_value
                )

                risk_category = point[
                    "risk_category"
                ]

                risk_counts[
                    risk_category
                ] += 1

                # Skip invalid values from
                # the GeoJSON result.

                if risk_category == "no_data":
                    continue

                hazard_score = point[
                    "hazard_score"
                ]

                hazard_scores.append(
                    hazard_score
                )

                feature = {
                    "type": "Feature",

                    "geometry": {
                        "type": "Point",

                        "coordinates": [
                            float(longitude),
                            float(latitude),
                        ],
                    },

                    "properties": {
                        "date":
                            date,

                        "rainfall_mm":
                            point[
                                "rainfall_mm"
                            ],

                        "hazard_score":
                            hazard_score,

                        "risk_category":
                            risk_category,

                        "rainfall_category":
                            point[
                                "rainfall_category"
                            ],
                    },
                }

                features.append(
                    feature
                )

                # Track maximum-risk point.

                if (
                    maximum_risk is None
                    or hazard_score
                    > maximum_risk[
                        "hazard_score"
                    ]
                ):

                    maximum_risk = {
                        "latitude":
                            float(latitude),

                        "longitude":
                            float(longitude),

                        "rainfall_mm":
                            point[
                                "rainfall_mm"
                            ],

                        "hazard_score":
                            hazard_score,

                        "risk_category":
                            risk_category,

                        "rainfall_category":
                            point[
                                "rainfall_category"
                            ],
                    }

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        valid_count = len(
            hazard_scores
        )

        if valid_count > 0:

            mean_hazard_score = float(
                np.mean(
                    hazard_scores
                )
            )

            maximum_hazard_score = float(
                np.max(
                    hazard_scores
                )
            )

        else:

            mean_hazard_score = None

            maximum_hazard_score = None

        return {
            "type":
                "FeatureCollection",

            "features":
                features,

            "properties": {

                "date":
                    date,

                "variable":
                    "RAINFALL",

                "units":
                    "mm",

                "risk_model":
                    "Rainfall Hazard Index v1",

                "score_range": {
                    "minimum": 0,
                    "maximum": 100,
                },

                "thresholds": {
                    "heavy_mm":
                        HEAVY_THRESHOLD_MM,

                    "very_heavy_mm":
                        VERY_HEAVY_THRESHOLD_MM,

                    "extremely_heavy_mm":
                        EXTREMELY_HEAVY_THRESHOLD_MM,
                },

                "grid": {
                    "latitude_count":
                        len(latitudes),

                    "longitude_count":
                        len(longitudes),

                    "total_points":
                        int(
                            values.size
                        ),

                    "valid_points":
                        valid_count,
                },

                "risk_distribution":
                    risk_counts,

                "statistics": {
                    "mean_hazard_score":
                        mean_hazard_score,

                    "maximum_hazard_score":
                        maximum_hazard_score,
                },

                "maximum_risk":
                    maximum_risk,
            },
        }

    finally:

        dataset.close()


# ============================================================
# RISK SUMMARY
# ============================================================

def get_climate_risk_summary(
    date: str,
) -> dict[str, Any]:
    """
    Return only the summary information
    for a date.

    This will later power the dashboard.
    """

    grid = get_climate_risk_grid(
        date
    )

    properties = grid[
        "properties"
    ]

    return {
        "date":
            properties["date"],

        "variable":
            properties["variable"],

        "units":
            properties["units"],

        "risk_model":
            properties["risk_model"],

        "score_range":
            properties["score_range"],

        "thresholds":
            properties["thresholds"],

        "grid":
            properties["grid"],

        "risk_distribution":
            properties["risk_distribution"],

        "statistics":
            properties["statistics"],

        "maximum_risk":
            properties["maximum_risk"],
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    TEST_DATE = "2024-07-15"

    print("=" * 70)

    print(
        "INDIA CLIMATE DIGITAL TWIN"
    )

    print(
        "CLIMATE RISK ENGINE TEST"
    )

    print("=" * 70)

    print()

    print(
        f"Date: {TEST_DATE}"
    )

    print()

    print(
        "RISK MODEL"
    )

    print("-" * 70)

    print(
        "Rainfall Hazard Index v1"
    )

    print(
        "Score range: 0 - 100"
    )

    print()

    print(
        "RAINFALL THRESHOLDS"
    )

    print("-" * 70)

    print(
        f"Heavy: "
        f"{HEAVY_THRESHOLD_MM} mm"
    )

    print(
        f"Very Heavy: "
        f"{VERY_HEAVY_THRESHOLD_MM} mm"
    )

    print(
        f"Extremely Heavy: "
        f"{EXTREMELY_HEAVY_THRESHOLD_MM} mm"
    )

    print()

    result = get_climate_risk_summary(
        TEST_DATE
    )

    print(
        "RISK DISTRIBUTION"
    )

    print("-" * 70)

    distribution = (
        result[
            "risk_distribution"
        ]
    )

    print(
        f"Low: "
        f"{distribution['low']}"
    )

    print(
        f"Moderate: "
        f"{distribution['moderate']}"
    )

    print(
        f"High: "
        f"{distribution['high']}"
    )

    print(
        f"Extreme: "
        f"{distribution['extreme']}"
    )

    print()

    print(
        "RISK STATISTICS"
    )

    print("-" * 70)

    statistics = (
        result[
            "statistics"
        ]
    )

    print(
        "Mean hazard score: "
        f"{statistics['mean_hazard_score']}"
    )

    print(
        "Maximum hazard score: "
        f"{statistics['maximum_hazard_score']}"
    )

    print()

    print(
        "MAXIMUM RISK LOCATION"
    )

    print("-" * 70)

    maximum = result[
        "maximum_risk"
    ]

    if maximum:

        print(
            f"Latitude: "
            f"{maximum['latitude']}"
        )

        print(
            f"Longitude: "
            f"{maximum['longitude']}"
        )

        print(
            f"Rainfall: "
            f"{maximum['rainfall_mm']:.2f} mm"
        )

        print(
            f"Hazard score: "
            f"{maximum['hazard_score']}"
        )

        print(
            f"Risk category: "
            f"{maximum['risk_category']}"
        )

        print(
            f"Rainfall category: "
            f"{maximum['rainfall_category']}"
        )

    print()

    print("=" * 70)

    print(
        "CLIMATE RISK ENGINE TEST COMPLETE"
    )

    print("=" * 70)