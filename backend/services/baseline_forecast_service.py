"""
India Climate Digital Twin
Step 11C - Baseline Rainfall Forecast

7-day moving-average baseline.

The model uses only historical observations preceding
the forecast date. No future information is used.
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

WINDOW_SIZE = 7


# ============================================================
# DATASET
# ============================================================

def load_dataset() -> xr.Dataset:

    if not DATASET_PATH.exists():

        raise FileNotFoundError(
            f"IMD dataset not found: {DATASET_PATH}"
        )

    return xr.open_dataset(
        DATASET_PATH
    )


# ============================================================
# INDIA-WIDE DAILY SERIES
# ============================================================

def get_daily_series() -> list[dict]:

    with load_dataset() as ds:

        rainfall = ds["RAINFALL"]

        result = []

        dates = (
            ds.TIME
            .dt.strftime("%Y-%m-%d")
            .values
        )

        for index, date in enumerate(dates):

            values = (
                rainfall
                .isel(TIME=index)
                .values
                .astype(np.float64)
            )

            valid = values[
                np.isfinite(values)
            ]

            if valid.size == 0:
                continue

            result.append({
                "date": str(date),
                "rainfall_mm": float(
                    np.mean(valid)
                ),
            })

        return result


# ============================================================
# MOVING-AVERAGE FORECAST
# ============================================================

def forecast_next_day(
    history: list[dict],
    window_size: int = WINDOW_SIZE,
) -> float:

    if len(history) < window_size:

        raise ValueError(
            f"At least {window_size} "
            "historical observations are "
            "required."
        )

    recent_values = [
        float(item["rainfall_mm"])
        for item in history[
            -window_size:
        ]
    ]

    return float(
        np.mean(recent_values)
    )


# ============================================================
# WALK-FORWARD FORECAST
# ============================================================

def generate_test_forecasts(
    test_start: str = "2024-11-01",
    test_end: str = "2024-12-31",
) -> list[dict]:

    series = get_daily_series()

    forecasts = []

    for index, item in enumerate(series):

        current_date = item["date"]

        if current_date < test_start:
            continue

        if current_date > test_end:
            break

        history = series[:index]

        if len(history) < WINDOW_SIZE:
            continue

        prediction = forecast_next_day(
            history
        )

        actual = float(
            item["rainfall_mm"]
        )

        forecasts.append({
            "date": current_date,
            "actual_rainfall_mm": actual,
            "forecast_rainfall_mm": prediction,
        })

    return forecasts


# ============================================================
# METRICS
# ============================================================

def calculate_metrics(
    forecasts: list[dict],
) -> dict:

    if not forecasts:

        raise ValueError(
            "No forecast observations available."
        )

    actual = np.array([
        item["actual_rainfall_mm"]
        for item in forecasts
    ])

    predicted = np.array([
        item["forecast_rainfall_mm"]
        for item in forecasts
    ])

    errors = predicted - actual

    mae = np.mean(
        np.abs(errors)
    )

    rmse = np.sqrt(
        np.mean(
            errors ** 2
        )
    )

    bias = np.mean(
        errors
    )

    return {
        "observations": int(
            len(forecasts)
        ),
        "mae_mm": float(mae),
        "rmse_mm": float(rmse),
        "bias_mm": float(bias),
    }


# ============================================================
# TEST
# ============================================================

def run_test() -> None:

    print("=" * 70)
    print("INDIA CLIMATE DIGITAL TWIN")
    print("STEP 11C - BASELINE FORECAST")
    print("=" * 70)

    print()
    print("Model: 7-day moving average")

    print(
        f"Window: {WINDOW_SIZE} days"
    )

    print(
        "Training period: "
        "2024-01-01 to 2024-10-31"
    )

    print(
        "Test period: "
        "2024-11-01 to 2024-12-31"
    )

    forecasts = generate_test_forecasts()

    metrics = calculate_metrics(
        forecasts
    )

    print()
    print("-" * 70)
    print("FORECAST PERFORMANCE")
    print("-" * 70)

    print(
        f"Observations: "
        f"{metrics['observations']}"
    )

    print(
        f"MAE: "
        f"{metrics['mae_mm']:.4f} mm"
    )

    print(
        f"RMSE: "
        f"{metrics['rmse_mm']:.4f} mm"
    )

    print(
        f"Bias: "
        f"{metrics['bias_mm']:.4f} mm"
    )

    print()
    print("-" * 70)
    print("SAMPLE FORECASTS")
    print("-" * 70)

    for item in forecasts[:5]:

        print(
            f"{item['date']} | "
            f"Actual: "
            f"{item['actual_rainfall_mm']:.4f} mm | "
            f"Forecast: "
            f"{item['forecast_rainfall_mm']:.4f} mm"
        )

    print()
    print("=" * 70)
    print("BASELINE FORECAST TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_test()
