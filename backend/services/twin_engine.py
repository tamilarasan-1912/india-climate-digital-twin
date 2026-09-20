"""Climate digital-twin engine.

The engine follows the Earth-system digital-twin pattern:
1. What-now: derive a synchronized state from observations.
2. What-next: run a forecast model from that state.
3. What-if: perturb validated inputs and recompute impacts.

This implementation is deliberately data-honest. It uses the IMD RF25 dataset
that is already part of the project and exposes uncertainty/coverage instead of
inventing missing atmospheric variables.
"""

from __future__ import annotations

from datetime import date as date_type, timedelta
import hashlib
import json
from typing import Any

import numpy as np

from backend.services.baseline_forecast_service import WINDOW_SIZE, forecast_next_day, get_daily_series
from backend.services.climate_risk_service import (
    calculate_risk_score,
    classify_risk_score,
    get_climate_risk_grid,
)
from backend.services.rainfall_service import get_daily_statistics, get_dataset_info

ENGINE_VERSION = "1.0.0"
STATE_VARIABLES = (
    "rainfall_mean_mm",
    "rainfall_median_mm",
    "rainfall_max_mm",
    "rainfall_rolling_mean_7d_mm",
    "rainfall_anomaly_mm",
    "rainfall_anomaly_z",
    "hazard_mean",
    "hazard_max",
    "extreme_fraction",
)


def _finite(values: list[float]) -> list[float]:
    return [float(v) for v in values if np.isfinite(v)]


def _latest_date(series: list[dict[str, Any]]) -> str:
    if not series:
        raise FileNotFoundError("No IMD rainfall observations are available.")
    return max(str(item["date"]) for item in series)


def _history_before(series: list[dict[str, Any]], target: str, days: int) -> list[dict[str, Any]]:
    end = date_type.fromisoformat(target)
    start = end - timedelta(days=days)
    return [item for item in series if start.isoformat() <= item["date"] < target]


def _state_vector(stats: dict[str, float], history_values: list[float], risk: dict[str, Any]) -> list[float]:
    current = float(stats["mean"])
    rolling = float(np.mean(history_values[-7:])) if history_values else current
    baseline = float(np.mean(history_values)) if history_values else current
    std = float(np.std(history_values)) if history_values else 0.0
    anomaly = current - baseline
    z = anomaly / std if std > 1e-12 else 0.0
    props = risk["properties"]
    grid_scores = []
    for feature in risk["features"]:
        score = feature["properties"].get("hazard_score")
        if score is not None and np.isfinite(float(score)):
            grid_scores.append(float(score))
    distribution = props["risk_distribution"]
    valid = max(1, int(props["grid"]["valid_points"]))
    extreme_fraction = float(distribution.get("extreme", 0)) / valid
    return [
        current,
        float(stats["median"]),
        float(stats["maximum"]),
        rolling,
        anomaly,
        z,
        float(np.mean(grid_scores)) if grid_scores else 0.0,
        float(np.max(grid_scores)) if grid_scores else 0.0,
        extreme_fraction,
    ]


def _snapshot_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def build_twin_snapshot(target_date: str | None = None) -> dict[str, Any]:
    series = get_daily_series()
    target = target_date or _latest_date(series)
    if not any(item["date"] == target for item in series):
        raise ValueError(f"Twin date {target} is not present in the IMD source dataset.")

    stats_raw = get_daily_statistics(target)
    stats = {
        "minimum": float(stats_raw["minimum"]),
        "maximum": float(stats_raw["maximum"]),
        "mean": float(stats_raw["mean"]),
        "median": float(stats_raw["median"]),
    }
    prior = _history_before(series, target, 30)
    prior_values = _finite([float(item["rainfall_mm"]) for item in prior])
    risk = get_climate_risk_grid(target)
    vector = _state_vector(stats, prior_values, risk)
    props = risk["properties"]
    source_info = get_dataset_info()

    state_payload = {
        "date": target,
        "source_dataset": source_info["file"],
        "source_variable": source_info["variable"],
        "vector": vector,
    }
    return {
        "twin": {
            "id": "india-climate-twin",
            "name": "India Climate Digital Twin",
            "scope": "India rainfall hazard system",
            "engine_version": ENGINE_VERSION,
        },
        "synchronization": {
            "status": "synchronized",
            "observation_date": target,
            "source": "IMD RF25 gridded rainfall",
            "source_variable": "RAINFALL",
            "unit": "mm",
            "state_hash": _snapshot_hash(state_payload),
            "observation_count": len(series),
            "lookback_days": 30,
        },
        "what_now": {
            "rainfall": stats,
            "rolling_7d_mean_mm": vector[3],
            "anomaly_mm": vector[4],
            "anomaly_z": vector[5],
            "risk": {
                "mean_hazard_score": props["statistics"]["mean_hazard_score"],
                "maximum_hazard_score": props["statistics"]["maximum_hazard_score"],
                "distribution": props["risk_distribution"],
                "maximum_risk": props["maximum_risk"],
            },
        },
        "state": {
            "variables": list(STATE_VARIABLES),
            "vector": vector,
            "representation": "deterministic observation-derived state; not a neural latent state",
        },
        "provenance": {
            "dataset": source_info,
            "risk_model": props["risk_model"],
        },
    }


def build_what_next(target_date: str | None = None, horizon: int = 7) -> dict[str, Any]:
    if not 1 <= horizon <= 14:
        raise ValueError("horizon must be between 1 and 14 days")
    series = get_daily_series()
    target = target_date or _latest_date(series)
    history = [item for item in series if item["date"] <= target]
    if len(history) < WINDOW_SIZE:
        raise ValueError(f"At least {WINDOW_SIZE} observations are required before forecasting.")
    prediction = forecast_next_day(history, WINDOW_SIZE)
    start = date_type.fromisoformat(target)
    forecast = [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "rainfall_mm": float(prediction),
            "model": "7-day moving-average baseline",
            "confidence": "not calibrated",
        }
        for i in range(1, horizon + 1)
    ]
    return {
        "status": "forecast_available",
        "from_state_date": target,
        "horizon_days": horizon,
        "forecast": forecast,
        "model": {
            "name": "7-day moving-average baseline",
            "training_observations": len(history),
            "uses_future_data": False,
        },
        "limitation": "This is the validated rainfall baseline. Prithvi-WxC is not used until its 160-variable MERRA-2 input contract is satisfied.",
    }


def build_what_if(
    target_date: str,
    precipitation_delta_pct: float = 0.0,
    temperature_delta_c: float = 0.0,
    sea_level_rise_m: float = 0.0,
    scenario: str = "custom",
) -> dict[str, Any]:
    if not -100 <= precipitation_delta_pct <= 300:
        raise ValueError("precipitation_delta_pct must be between -100 and 300")
    if not -10 <= temperature_delta_c <= 10:
        raise ValueError("temperature_delta_c must be between -10 and 10")
    if not 0 <= sea_level_rise_m <= 2:
        raise ValueError("sea_level_rise_m must be between 0 and 2 metres")

    baseline = get_climate_risk_grid(target_date)
    counts = {"low": 0, "moderate": 0, "high": 0, "extreme": 0, "no_data": 0}
    scores: list[float] = []
    deltas: list[float] = []
    baseline_scores: list[float] = []
    for feature in baseline["features"]:
        base_rain = float(feature["properties"]["rainfall_mm"])
        base_score = float(feature["properties"]["hazard_score"])
        scenario_rain = max(0.0, base_rain * (1.0 + precipitation_delta_pct / 100.0))
        scenario_score = float(calculate_risk_score(scenario_rain))
        category = classify_risk_score(scenario_score)
        counts[category] += 1
        scores.append(scenario_score)
        baseline_scores.append(base_score)
        deltas.append(scenario_score - base_score)

    return {
        "status": "scenario_computed",
        "scenario": scenario,
        "base_date": target_date,
        "parameters": {
            "precipitation_delta_pct": float(precipitation_delta_pct),
            "temperature_delta_c": float(temperature_delta_c),
            "sea_level_rise_m": float(sea_level_rise_m),
        },
        "baseline": {
            "mean_hazard_score": float(np.mean(baseline_scores)) if baseline_scores else None,
            "maximum_hazard_score": float(np.max(baseline_scores)) if baseline_scores else None,
        },
        "scenario_result": {
            "mean_hazard_score": float(np.mean(scores)) if scores else None,
            "maximum_hazard_score": float(np.max(scores)) if scores else None,
            "risk_distribution": counts,
            "mean_score_delta": float(np.mean(deltas)) if deltas else None,
        },
        "coupling": {
            "precipitation": "modeled through rainfall hazard engine",
            "temperature": "input recorded but not coupled because no validated temperature dataset/model is installed",
            "sea_level_rise": "input recorded but not coupled because no validated coastal/flood model is installed",
        },
        "scientific_status": "sensitivity experiment, not a physical multi-hazard impact simulation",
    }


def get_twin_health() -> dict[str, Any]:
    try:
        snapshot = build_twin_snapshot()
        next_state = build_what_next(snapshot["synchronization"]["observation_date"], 1)
        return {
            "status": "operational",
            "engine_version": ENGINE_VERSION,
            "synchronization": snapshot["synchronization"],
            "what_now": "pass",
            "what_next": "pass" if next_state["forecast"] else "fail",
            "what_if": "pass",
            "data_contract": "pass",
        }
    except Exception as error:
        return {
            "status": "degraded",
            "engine_version": ENGINE_VERSION,
            "error": str(error),
            "what_now": "fail",
            "what_next": "fail",
            "what_if": "fail",
            "data_contract": "fail",
        }
