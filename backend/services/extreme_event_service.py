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

# Daily rainfall classification used by IMD.
#
# Heavy Rain:
#       64.5 - 115.5 mm
#
# Very Heavy Rain:
#       115.6 - 204.4 mm
#
# Extremely Heavy Rain:
#       >= 204.5 mm
#
# Values below 64.5 mm are not considered extreme
# rainfall events by this detector.

HEAVY_THRESHOLD_MM = 64.5

VERY_HEAVY_THRESHOLD_MM = 115.6

EXTREMELY_HEAVY_THRESHOLD_MM = 204.5


# ============================================================
# DATASET LOADING
# ============================================================

def load_dataset() -> xr.Dataset:
    """
    Open the IMD rainfall NetCDF dataset.

    Returns
    -------
    xarray.Dataset
        Open rainfall dataset.
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
    Validate and retrieve rainfall data for a date.

    Parameters
    ----------
    dataset:
        Open IMD rainfall dataset.

    date:
        Date in YYYY-MM-DD format.

    Returns
    -------
    xarray.DataArray
        Rainfall grid for the requested date.
    """

    try:
        selected = dataset["RAINFALL"].sel(
            TIME=date
        )

        return selected

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
    Convert rainfall values into a clean float32 array.

    Invalid values are converted to NaN.
    """

    values = np.asarray(
        values,
        dtype=np.float32,
    )

    values[
        ~np.isfinite(values)
    ] = np.nan

    # Safety check for impossible numerical values.
    values[
        np.abs(values) > 10000
    ] = np.nan

    return values


# ============================================================
# CLASSIFY ONE RAINFALL VALUE
# ============================================================

def classify_rainfall(
    rainfall_mm: float,
) -> str:
    """
    Classify rainfall using IMD thresholds.

    Returns
    -------
    str

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
# EVENT SEVERITY
# ============================================================

def severity_score(
    rainfall_mm: float,
) -> int:
    """
    Convert rainfall intensity into a simple severity score.

    0 = no extreme event
    1 = heavy
    2 = very heavy
    3 = extremely heavy
    """

    category = classify_rainfall(
        rainfall_mm
    )

    scores = {
        "no_data": 0,
        "no_event": 0,
        "heavy": 1,
        "very_heavy": 2,
        "extremely_heavy": 3,
    }

    return scores[category]


# ============================================================
# DETECT EXTREME RAINFALL GRID
# ============================================================

def detect_extreme_rainfall(
    date: str,
) -> dict[str, Any]:
    """
    Detect all heavy, very heavy and extremely heavy
    rainfall grid points for a specific date.

    Only grid cells >= 64.5 mm are returned.

    Returns
    -------
    dict
        Structured extreme-event result.
    """

    dataset = load_dataset()

    try:
        rainfall = validate_date(
            dataset,
            date,
        )

        values = clean_rainfall_values(
            rainfall.values
        )

        latitudes = np.asarray(
            dataset["LATITUDE"].values,
            dtype=float,
        )

        longitudes = np.asarray(
            dataset["LONGITUDE"].values,
            dtype=float,
        )

        # ----------------------------------------------------
        # Create coordinate grid
        # ----------------------------------------------------

        longitude_grid, latitude_grid = np.meshgrid(
            longitudes,
            latitudes,
        )

        # ----------------------------------------------------
        # Valid rainfall mask
        # ----------------------------------------------------

        valid_mask = np.isfinite(
            values
        )

        # ----------------------------------------------------
        # Extreme-event mask
        # ----------------------------------------------------

        event_mask = (
            valid_mask
            & (
                values
                >= HEAVY_THRESHOLD_MM
            )
        )

        # ----------------------------------------------------
        # Extract event cells
        # ----------------------------------------------------

        event_indices = np.argwhere(
            event_mask
        )

        events = []

        for lat_index, lon_index in event_indices:

            rainfall_value = float(
                values[
                    lat_index,
                    lon_index,
                ]
            )

            latitude = float(
                latitude_grid[
                    lat_index,
                    lon_index,
                ]
            )

            longitude = float(
                longitude_grid[
                    lat_index,
                    lon_index,
                ]
            )

            category = classify_rainfall(
                rainfall_value
            )

            events.append(
                {
                    "latitude": latitude,

                    "longitude": longitude,

                    "rainfall_mm":
                        rainfall_value,

                    "category":
                        category,

                    "severity":
                        severity_score(
                            rainfall_value
                        ),

                    "date":
                        date,
                }
            )

        # ----------------------------------------------------
        # Sort strongest events first
        # ----------------------------------------------------

        events.sort(
            key=lambda event:
                event["rainfall_mm"],
            reverse=True,
        )

        # ----------------------------------------------------
        # Category counts
        # ----------------------------------------------------

        heavy_count = sum(
            event["category"] == "heavy"
            for event in events
        )

        very_heavy_count = sum(
            event["category"] == "very_heavy"
            for event in events
        )

        extremely_heavy_count = sum(
            event["category"] == "extremely_heavy"
            for event in events
        )

        # ----------------------------------------------------
        # Maximum event
        # ----------------------------------------------------

        maximum_event = (
            events[0]
            if events
            else None
        )

        # ----------------------------------------------------
        # Return result
        # ----------------------------------------------------

        return {
            "date": date,

            "variable": "RAINFALL",

            "units": "mm",

            "thresholds": {
                "heavy_mm":
                    HEAVY_THRESHOLD_MM,

                "very_heavy_mm":
                    VERY_HEAVY_THRESHOLD_MM,

                "extremely_heavy_mm":
                    EXTREMELY_HEAVY_THRESHOLD_MM,
            },

            "summary": {
                "total_extreme_points":
                    len(events),

                "heavy_points":
                    heavy_count,

                "very_heavy_points":
                    very_heavy_count,

                "extremely_heavy_points":
                    extremely_heavy_count,

                "maximum_rainfall_mm":
                    (
                        maximum_event[
                            "rainfall_mm"
                        ]
                        if maximum_event
                        else None
                    ),

                "maximum_location": (
                    {
                        "latitude":
                            maximum_event[
                                "latitude"
                            ],

                        "longitude":
                            maximum_event[
                                "longitude"
                            ],
                    }
                    if maximum_event
                    else None
                ),
            },

            "events": events,
        }

    finally:
        dataset.close()


# ============================================================
# EXTREME RAINFALL AS GEOJSON
# ============================================================

def get_extreme_rainfall_geojson(
    date: str,
) -> dict[str, Any]:
    """
    Convert detected extreme rainfall events
    into GeoJSON.

    Only rainfall >= 64.5 mm is included.
    """

    result = detect_extreme_rainfall(
        date
    )

    features = []

    for event in result["events"]:

        features.append(
            {
                "type": "Feature",

                "geometry": {
                    "type": "Point",

                    "coordinates": [
                        event["longitude"],
                        event["latitude"],
                    ],
                },

                "properties": {
                    "date":
                        event["date"],

                    "rainfall_mm":
                        event["rainfall_mm"],

                    "category":
                        event["category"],

                    "severity":
                        event["severity"],
                },
            }
        )

    return {
        "type": "FeatureCollection",

        "features": features,

        "properties": {
            "date": date,

            "variable":
                "RAINFALL",

            "units":
                "mm",

            "event_threshold_mm":
                HEAVY_THRESHOLD_MM,

            "event_count":
                len(features),
        },
    }


# ============================================================
# EXTREME EVENT SUMMARY
# ============================================================

def get_extreme_event_summary(
    date: str,
) -> dict[str, Any]:
    """
    Return only the summary of extreme rainfall
    for a given date.

    This endpoint will later be useful for the
    dashboard statistics panel.
    """

    result = detect_extreme_rainfall(
        date
    )

    return {
        "date":
            result["date"],

        "variable":
            result["variable"],

        "units":
            result["units"],

        "thresholds":
            result["thresholds"],

        "summary":
            result["summary"],
    }


# ============================================================
# MAIN TEST
# ============================================================

if __name__ == "__main__":

    TEST_DATE = "2024-07-15"

    print("=" * 70)

    print(
        "INDIA CLIMATE DIGITAL TWIN"
    )

    print(
        "EXTREME RAINFALL DETECTION TEST"
    )

    print("=" * 70)

    print()

    print(
        f"Date: {TEST_DATE}"
    )

    print()

    print(
        "IMD THRESHOLDS"
    )

    print("-" * 70)

    print(
        f"Heavy rainfall: "
        f">= {HEAVY_THRESHOLD_MM} mm"
    )

    print(
        f"Very heavy rainfall: "
        f">= {VERY_HEAVY_THRESHOLD_MM} mm"
    )

    print(
        f"Extremely heavy rainfall: "
        f">= {EXTREMELY_HEAVY_THRESHOLD_MM} mm"
    )

    print()

    result = detect_extreme_rainfall(
        TEST_DATE
    )

    print(
        "EXTREME EVENT SUMMARY"
    )

    print("-" * 70)

    print(
        f"Total extreme grid points: "
        f"{result['summary']['total_extreme_points']}"
    )

    print(
        f"Heavy points: "
        f"{result['summary']['heavy_points']}"
    )

    print(
        f"Very heavy points: "
        f"{result['summary']['very_heavy_points']}"
    )

    print(
        f"Extremely heavy points: "
        f"{result['summary']['extremely_heavy_points']}"
    )

    print(
        f"Maximum rainfall: "
        f"{result['summary']['maximum_rainfall_mm']} mm"
    )

    print()

    if result["summary"]["maximum_location"]:
        location = (
            result["summary"]
            ["maximum_location"]
        )

        print(
            "Maximum rainfall location:"
        )

        print(
            f"Latitude: "
            f"{location['latitude']}"
        )

        print(
            f"Longitude: "
            f"{location['longitude']}"
        )

    print()

    print(
        "TOP EXTREME EVENTS"
    )

    print("-" * 70)

    for index, event in enumerate(
        result["events"][:10],
        start=1,
    ):

        print(
            f"{index}. "
            f"{event['rainfall_mm']:.2f} mm | "
            f"{event['category']} | "
            f"Lat {event['latitude']:.2f} | "
            f"Lon {event['longitude']:.2f}"
        )

    print()

    print("=" * 70)

    print(
        "EXTREME RAINFALL DETECTION COMPLETE"
    )

    print("=" * 70)