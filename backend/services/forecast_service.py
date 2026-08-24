"""
India Climate Digital Twin
Historical Rainfall Time-Series Service

Step 11B:
Extracts reproducible daily rainfall time-series
statistics from the validated IMD NetCDF dataset.

No synthetic data is generated.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATASET_PATH = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "RF25_ind2024_rfp25.nc"
)


# ============================================================
# DATASET LOADING
# ============================================================

def load_forecast_dataset() -> xr.Dataset:

    if not DATASET_PATH.exists():

        raise FileNotFoundError(
            f"IMD dataset not found: {DATASET_PATH}"
        )

    return xr.open_dataset(
        DATASET_PATH
    )


# ============================================================
# VALIDATE DATE
# ============================================================

def validate_date(
    date: str,
) -> None:

    try:

        np.datetime64(date)

    except Exception as error:

        raise ValueError(
            f"Invalid date: {date}"
        ) from error


# ============================================================
# DAILY INDIA STATISTICS
# ============================================================

def get_daily_india_statistics(
    date: str,
) -> dict:

    validate_date(date)

    with load_forecast_dataset() as ds:

        if date not in ds.TIME.dt.strftime(
            "%Y-%m-%d"
        ).values:

            raise ValueError(
                f"Date {date} is outside "
                "the available dataset."
            )

        rainfall = ds[
            "RAINFALL"
        ].sel(
            TIME=date
        )

        values = rainfall.values.astype(
            np.float64
        )

        valid = values[
            np.isfinite(values)
        ]

        if valid.size == 0:

            raise ValueError(
                f"No valid rainfall data "
                f"available for {date}."
            )

        return {

            "date": date,

            "variable": "RAINFALL",

            "unit": "mm",

            "provider": "IMD",

            "valid_grid_points":
                int(valid.size),

            "mean_rainfall_mm":
                float(np.mean(valid)),

            "minimum_rainfall_mm":
                float(np.min(valid)),

            "maximum_rainfall_mm":
                float(np.max(valid)),

            "total_grid_rainfall_mm":
                float(np.sum(valid)),

        }


# ============================================================
# DAILY TIME SERIES
# ============================================================

def get_india_daily_timeseries() -> list[dict]:

    with load_forecast_dataset() as ds:

        rainfall = ds[
            "RAINFALL"
        ]

        dates = (
            ds.TIME
            .dt.strftime("%Y-%m-%d")
            .values
        )

        result = []

        for index, date in enumerate(
            dates
        ):

            values = rainfall.isel(
                TIME=index
            ).values.astype(
                np.float64
            )

            valid = values[
                np.isfinite(values)
            ]

            if valid.size == 0:

                continue

            result.append({

                "date": str(date),

                "mean_rainfall_mm":
                    float(
                        np.mean(valid)
                    ),

                "minimum_rainfall_mm":
                    float(
                        np.min(valid)
                    ),

                "maximum_rainfall_mm":
                    float(
                        np.max(valid)
                    ),

                "valid_grid_points":
                    int(valid.size),

            })

        return result


# ============================================================
# GRID-POINT TIME SERIES
# ============================================================

def get_grid_point_timeseries(
    latitude: float,
    longitude: float,
) -> list[dict]:

    with load_forecast_dataset() as ds:

        rainfall = ds[
            "RAINFALL"
        ].sel(
            LATITUDE=latitude,
            LONGITUDE=longitude,
            method="nearest",
        )

        actual_latitude = float(
            rainfall.LATITUDE.values
        )

        actual_longitude = float(
            rainfall.LONGITUDE.values
        )

        dates = (
            ds.TIME
            .dt.strftime("%Y-%m-%d")
            .values
        )

        values = rainfall.values.astype(
            np.float64
        )

        result = []

        for date, value in zip(
            dates,
            values,
        ):

            rainfall_value = (
                None
                if not np.isfinite(value)
                else float(value)
            )

            result.append({

                "date": str(date),

                "latitude":
                    actual_latitude,

                "longitude":
                    actual_longitude,

                "rainfall_mm":
                    rainfall_value,

            })

        return result
