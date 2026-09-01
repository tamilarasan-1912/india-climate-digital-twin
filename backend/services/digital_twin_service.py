"""Operational integration services for the India Climate Digital Twin.

This module exposes only computations backed by datasets already present in the
repository. It deliberately does not invent temperature, flood, population,
or AI-model predictions when those datasets/models are unavailable.
"""

from __future__ import annotations

import csv
from datetime import date as date_type, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from backend.services.ai_forecast_service import get_ai_model_info
from backend.services.baseline_forecast_service import (
    WINDOW_SIZE,
    get_daily_series,
    forecast_next_day,
)
from backend.services.climate_risk_service import (
    calculate_point_risk,
    calculate_risk_score,
    classify_rainfall,
    classify_risk_score,
    get_climate_risk_grid,
    HEAVY_THRESHOLD_MM,
    VERY_HEAVY_THRESHOLD_MM,
    EXTREMELY_HEAVY_THRESHOLD_MM,
)
from backend.services.merra2_input_validator import discover_files, validate_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TWIN_STATE_CSV = PROJECT_ROOT / "data/india/chennai/twin_state/chennai_twin_states.csv"
FUSED_CSV = PROJECT_ROOT / "data/india/chennai/fused_features/chennai_prithvi_era5_fused_features.csv"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def get_twin_state_summary() -> dict[str, Any]:
    rows = _read_csv_rows(TWIN_STATE_CSV)
    fused = _read_csv_rows(FUSED_CSV)
    state_columns = [key for key in rows[0].keys() if key.startswith("twin_state_")] if rows else []
    return {
        "location": "Chennai",
        "state_dimension": len(state_columns),
        "observations": len(rows),
        "dates": [row["date"] for row in rows if row.get("date")],
        "state_source": "Prithvi-EO + ERA5 fused features",
        "fused_feature_dimension": max(0, len(fused[0]) - 5) if fused else 0,
        "status": "available" if rows else "unavailable",
        "scientific_note": "Current state is a deterministic PCA/SVD projection of the available fused observations; it is not a trained neural latent state.",
    }


def get_twin_state(date: str | None = None) -> dict[str, Any]:
    rows = _read_csv_rows(TWIN_STATE_CSV)
    if not rows:
        raise FileNotFoundError("Twin-state CSV is not available.")
    row = rows[-1] if date is None else next((item for item in rows if item.get("date") == date), None)
    if row is None:
        raise ValueError(f"Twin state date {date} is unavailable.")
    vector = [float(row[f"twin_state_{i:03d}"]) for i in range(128)]
    return {
        "date": row["date"],
        "location": {"name": "Chennai", "latitude": float(row["latitude"]), "longitude": float(row["longitude"])},
        "state_dimension": len(vector),
        "vector": vector,
        "provenance": ["Prithvi-EO", "ERA5"],
        "uncertainty": "not calibrated",
    }


def get_historical_rainfall(start: str | None = None, end: str | None = None, limit: int = 365) -> dict[str, Any]:
    series = get_daily_series()
    filtered = [item for item in series if (start is None or item["date"] >= start) and (end is None or item["date"] <= end)]
    if limit > 0:
        filtered = filtered[-min(limit, 5000):]
    return {"variable": "RAINFALL", "unit": "mm", "provider": "IMD", "count": len(filtered), "series": filtered}


def get_baseline_forecast(horizon: int = 7) -> dict[str, Any]:
    if not 1 <= horizon <= 14:
        raise ValueError("horizon must be between 1 and 14 days")
    series = get_daily_series()
    prediction = forecast_next_day(series, WINDOW_SIZE)
    last_date = date_type.fromisoformat(series[-1]["date"])
    forecast = []
    for offset in range(1, horizon + 1):
        forecast.append({"date": (last_date + timedelta(days=offset)).isoformat(), "rainfall_mm": prediction, "model": "7-day moving-average baseline"})
    return {"status": "baseline", "source": "IMD historical rainfall", "training_observations": len(series), "window_days": WINDOW_SIZE, "horizon_days": horizon, "confidence": "not calibrated", "forecast": forecast}


def get_model_catalog() -> dict[str, Any]:
    return {"models": [
        {"name": "IMD rainfall baseline", "type": "statistical baseline", "status": "active", "metrics": "available through /api/validation"},
        {"name": "Prithvi-EO V2 tiny", "type": "earth observation foundation model", "status": "feature extraction available", "metrics": "not calibrated for forecasting"},
        get_ai_model_info(),
    ]}


def get_validation_summary() -> dict[str, Any]:
    from backend.services.baseline_forecast_service import generate_test_forecasts, calculate_metrics
    forecasts = generate_test_forecasts()
    baseline = calculate_metrics(forecasts) if forecasts else None
    risk = get_climate_risk_grid("2024-07-15")["properties"]
    return {"baseline_rainfall_forecast": baseline, "risk_engine": {"date": "2024-07-15", "valid_points": risk["grid"]["valid_points"], "score_range": risk["score_range"], "risk_distribution": risk["risk_distribution"]}, "status": "validated for implemented rainfall components", "limitations": ["No calibrated AI forecast metrics", "No multi-variable forecast validation"]}


def explain_rainfall_risk(rainfall_mm: float) -> dict[str, Any]:
    point = calculate_point_risk(float(rainfall_mm))
    score = point["hazard_score"]
    if score is None:
        return {"status": "no_data", "drivers": []}
    drivers = [{"factor": "Observed rainfall intensity", "value": float(rainfall_mm), "unit": "mm", "role": "primary and only modeled driver"}]
    return {"status": "available", "risk": point, "drivers": drivers, "thresholds_mm": {"heavy": HEAVY_THRESHOLD_MM, "very_heavy": VERY_HEAVY_THRESHOLD_MM, "extremely_heavy": EXTREMELY_HEAVY_THRESHOLD_MM}, "limitation": "This explanation covers the current rainfall-only hazard model; it is not an explanation of a multi-hazard model."}


def simulate_rainfall_scenario(base_date: str, precipitation_delta_pct: float = 0.0, temperature_delta_c: float = 0.0, sea_level_rise_m: float = 0.0, scenario: str = "custom") -> dict[str, Any]:
    if not -100 <= precipitation_delta_pct <= 300:
        raise ValueError("precipitation_delta_pct must be between -100 and 300")
    if not -10 <= temperature_delta_c <= 10:
        raise ValueError("temperature_delta_c must be between -10 and 10")
    if not 0 <= sea_level_rise_m <= 2:
        raise ValueError("sea_level_rise_m must be between 0 and 2 metres")
    grid = get_climate_risk_grid(base_date)
    counts = {"low": 0, "moderate": 0, "high": 0, "extreme": 0, "no_data": 0}
    scores: list[float] = []
    for feature in grid["features"]:
        rainfall = float(feature["properties"]["rainfall_mm"]) * (1.0 + precipitation_delta_pct / 100.0)
        score = calculate_risk_score(rainfall)
        category = classify_risk_score(score)
        counts[category] += 1
        scores.append(score)
    return {
        "scenario": scenario,
        "base_date": base_date,
        "parameters": {"precipitation_delta_pct": precipitation_delta_pct, "temperature_delta_c": temperature_delta_c, "sea_level_rise_m": sea_level_rise_m},
        "screening_result": {"mean_hazard_score": float(np.mean(scores)) if scores else None, "maximum_hazard_score": float(np.max(scores)) if scores else None, "risk_distribution": counts},
        "modeled_effect": "precipitation perturbation only",
        "unmodeled_parameters": ["temperature_delta_c", "sea_level_rise_m"],
        "warning": "Scenario output is a transparent rainfall-hazard sensitivity experiment, not a physical flood, crop, population, or sea-level impact prediction.",
    }


def get_provenance() -> dict[str, Any]:
    return {"pipeline": [
        {"stage": "IMD rainfall", "status": "active", "dataset": "RF25_ind2024_rfp25.nc"},
        {"stage": "ERA5", "status": "available for Chennai fusion", "dataset": "data/india/chennai/era5"},
        {"stage": "Sentinel-2 historical", "status": "validated", "dataset": "70 readable TIFFs"},
        {"stage": "Prithvi-EO", "status": "feature extraction pipeline", "dataset": "data/india/chennai/prithvi_*"},
        {"stage": "Twin state", "status": "available", "dataset": str(TWIN_STATE_CSV.relative_to(PROJECT_ROOT)) if TWIN_STATE_CSV.exists() else None},
        {"stage": "Prithvi-WxC", "status": "blocked until compatible multi-variable atmospheric input is supplied", "dataset": None},
        {"stage": "MOSDAC", "status": "not connected", "dataset": None},
    ]}


def get_system_health() -> dict[str, Any]:
    files = {"imd_rainfall": PROJECT_ROOT / "backend/data/RF25_ind2024_rfp25.nc", "twin_state": TWIN_STATE_CSV, "fused_features": FUSED_CSV}
    checks = {name: path.exists() for name, path in files.items()}
    merra = discover_files()
    return {"status": "healthy" if all(checks.values()) else "degraded", "checks": checks, "merra2_files": len(merra), "ai_forecast": get_ai_model_info(), "notes": ["Health reports data availability; it does not claim that every planned model is operational."]}
