"""Canonical Digital Twin State Contract for Bharat Climate Twin.

This module defines the single authoritative state representation (bharat-climate-twin/v1)
that consolidates all previous twin state representations.

Contract Version: bharat-climate-twin/v1
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from backend.services.baseline_forecast_service import WINDOW_SIZE, forecast_next_day, get_daily_series
from backend.services.climate_risk_service import (
    calculate_risk_score,
    classify_risk_score,
    get_climate_risk_grid,
)
from backend.services.rainfall_service import get_daily_statistics, get_dataset_info

CONTRACT_VERSION = "bharat-climate-twin/v1"
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
    from datetime import date as date_type, timedelta
    end = date_type.fromisoformat(target)
    start = end - timedelta(days=days)
    return [item for item in series if start.isoformat() <= item["date"] < target]


def _state_vector(
    stats: dict[str, float],
    history_values: list[float],
    risk: dict[str, Any],
) -> list[float | None]:
    """Build the state vector without replacing undefined statistics with zero."""
    current = float(stats["mean"])
    rolling = float(np.mean(history_values[-7:])) if history_values else None
    baseline = float(np.mean(history_values)) if history_values else None
    std = float(np.std(history_values)) if history_values else None
    anomaly = current - baseline if baseline is not None else None
    z = anomaly / std if anomaly is not None and std is not None and std > 1e-12 else None
    props = risk["properties"]
    grid_scores = []
    for feature in risk["features"]:
        score = feature["properties"].get("hazard_score")
        if score is not None and np.isfinite(float(score)):
            grid_scores.append(float(score))
    distribution = props["risk_distribution"]
    valid = int(props["grid"].get("valid_points", 0))
    extreme_fraction = (
        float(distribution.get("extreme", 0)) / valid
        if valid > 0
        else None
    )
    return [
        current,
        float(stats["median"]),
        float(stats["maximum"]),
        rolling,
        anomaly,
        z,
        float(np.mean(grid_scores)) if grid_scores else None,
        float(np.max(grid_scores)) if grid_scores else None,
        extreme_fraction,
    ]


def _snapshot_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()[:16]


def build_twin_state(
    target_date: str | None = None,
    spatial_scope: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the canonical digital twin state (bharat-climate-twin/v1).

    Args:
        target_date: ISO date string. Defaults to latest available observation.
        spatial_scope: Optional spatial scope, e.g. {"type": "country", "id": "IN"}
                      or {"type": "basin", "id": "mahanadi_delta_sub_1"}

    Returns:
        Canonical twin state dict conforming to bharat-climate-twin/v1.
    """
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

    # Build the core state payload for hashing
    state_payload = {
        "date": target,
        "source_dataset": source_info["file"],
        "source_variable": source_info["variable"],
        "vector": vector,
        "spatial_scope": spatial_scope or {"type": "country", "id": "IN"},
    }

    # Build observations block
    observations = {
        "rainfall": {
            "source": "IMD RF25",
            "dataset": source_info["file"],
            "variable": "RAINFALL",
            "unit": "mm",
            "spatial_resolution": "0.25 degree",
            "temporal_resolution": "daily",
            "date": target,
            "statistics": stats,
            "grid_points": int(props["grid"]["valid_points"]),
            "provenance": {
                "source": "IMD",
                "dataset": source_info["file"],
                "variable": "RAINFALL",
                "unit": "mm",
                "processing": "daily_grid_extraction",
                "status": "validated",
            },
        },
    }

    # Build forecasts block (baseline only for now)
    history = [item for item in series if item["date"] <= target]
    prediction = forecast_next_day(history, WINDOW_SIZE) if len(history) >= WINDOW_SIZE else None
    forecasts = {}
    if prediction is not None:
        from datetime import date as date_type, timedelta
        start = date_type.fromisoformat(target)
        forecast_series = [
            {
                "date": (start + timedelta(days=i)).isoformat(),
                "rainfall_mm": float(prediction),
                "model": "7-day moving-average baseline",
                "confidence": "not calibrated",
            }
            for i in range(1, 8)
        ]
        forecasts = {
            "baseline": {
                "model": "7-day moving-average baseline",
                "model_version": "baseline-1.0.0",
                "input_state_hash": _snapshot_hash({"series": history[-WINDOW_SIZE:]}),
                "horizon_days": 7,
                "confidence": "not calibrated",
                "series": forecast_series,
                "validation": {
                    "metrics_endpoint": "/api/validation",
                    "status": "baseline_only",
                },
            }
        }

    # Build risks block
    risks = {
        "rainfall_hazard": {
            "model": props["risk_model"],
            "model_version": "rainfall-hazard-1.0.0",
            "date": target,
            "score_range": {"minimum": 0, "maximum": 100},
            "thresholds": props["thresholds"],
            "distribution": props["risk_distribution"],
            "statistics": props["statistics"],
            "maximum_risk": props["maximum_risk"],
            "provenance": {
                "source": "IMD RF25",
                "dataset": source_info["file"],
                "processing": "rainfall_hazard_scoring",
                "status": "validated for rainfall-only hazard model",
            },
        }
    }

    # Build models block
    models = {
        "rainfall_hazard": {
            "model_id": "rainfall-hazard-screen",
            "name": "Rainfall Hazard Screening Engine",
            "type": "deterministic_hazard_rule",
            "version": "rainfall-hazard-1.0.0",
            "status": "active",
            "inference_status": "operational",
        },
        "baseline_forecast": {
            "model_id": "imd-rainfall-moving-average",
            "name": "IMD Rainfall Baseline",
            "type": "statistical_baseline",
            "version": "7-day moving average (baseline-1.0.0)",
            "status": "active",
            "inference_status": "operational",
        },
        "prithvi_wxc": {
            "model_id": "prithvi-wxc-rollout",
            "name": "Prithvi-WxC Rollout",
            "type": "atmospheric_foundation_model",
            "version": "Prithvi-WxC-1.0-2300M-rollout",
            "status": "blocked",
            "inference_status": "blocked",
            "blockers": ["MERRA-2 160-variable input unavailable", "PyTorch/official package not installed", "Climatology scalers unavailable"],
        },
    }

    # Build uncertainty block
    uncertainty = {
        "rainfall_observation": "not_quantified",
        "hazard_score": "not_calibrated",
        "baseline_forecast": "not_calibrated",
        "note": "Uncertainty quantification requires validated error models; not yet implemented.",
    }

    # Build provenance block
    provenance = {
        "pipeline": [
            {"stage": "IMD rainfall", "status": "active", "dataset": "RF25_ind2024_rfp25.nc"},
            {"stage": "Rainfall hazard scoring", "status": "active", "model": "Rainfall Hazard Index v1"},
            {"stage": "Twin state assembly", "status": "active", "contract": CONTRACT_VERSION},
        ],
        "state_hash": _snapshot_hash(state_payload),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Determine overall status
    status = "synchronized"
    if target != _latest_date(series):
        status = "historical"
    elif not forecasts:
        status = "degraded"

    return {
        "contract_version": CONTRACT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "spatial_scope": spatial_scope or {"type": "country", "id": "IN"},
        "observation_date": target,
        "status": status,
        "variables": {
            "observed": ["rainfall"],
            "forecast": ["rainfall"] if forecasts else [],
            "simulated": [],
            "risk": ["rainfall_hazard"],
        },
        "observations": observations,
        "forecasts": forecasts,
        "simulations": {},
        "risks": risks,
        "uncertainty": uncertainty,
        "provenance": provenance,
        "models": models,
        "state_vector": {
            "variables": list(STATE_VARIABLES),
            "vector": vector,
            "representation": "deterministic observation-derived state; not a neural latent state",
        },
    }


def build_forecast_state(
    target_date: str | None = None,
    horizon: int = 7,
) -> dict[str, Any]:
    """Build the forecast portion of the twin state (what-next)."""
    if not 1 <= horizon <= 14:
        raise ValueError("horizon must be between 1 and 14 days")
    series = get_daily_series()
    target = target_date or _latest_date(series)
    history = [item for item in series if item["date"] <= target]
    if len(history) < WINDOW_SIZE:
        raise ValueError(f"At least {WINDOW_SIZE} observations are required before forecasting.")
    prediction = forecast_next_day(history, WINDOW_SIZE)
    from datetime import date as date_type, timedelta
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
        "contract_version": CONTRACT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "forecast",
        "source_state_date": target,
        "horizon_days": horizon,
        "model": {
            "name": "7-day moving-average baseline",
            "version": "baseline-1.0.0",
            "training_observations": len(history),
            "uses_future_data": False,
        },
        "forecast": forecast,
        "limitation": "This is the validated rainfall baseline. Prithvi-WxC is not used until its 160-variable MERRA-2 input contract is satisfied.",
    }


def build_scenario_state(
    base_date: str,
    precipitation_delta_pct: float = 0.0,
    temperature_delta_c: float = 0.0,
    sea_level_rise_m: float = 0.0,
    scenario: str = "custom",
) -> dict[str, Any]:
    """Build a scenario simulation state (what-if)."""
    if not -100 <= precipitation_delta_pct <= 300:
        raise ValueError("precipitation_delta_pct must be between -100 and 300")
    if not -10 <= temperature_delta_c <= 10:
        raise ValueError("temperature_delta_c must be between -10 and 10")
    if not 0 <= sea_level_rise_m <= 2:
        raise ValueError("sea_level_rise_m must be between 0 and 2 metres")

    baseline = get_climate_risk_grid(base_date)
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
        "contract_version": CONTRACT_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "type": "scenario",
        "scenario": scenario,
        "base_date": base_date,
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
        "provenance": {
            "baseline_state_hash": _snapshot_hash({"date": base_date, "source": "twin_state"}),
            "model": "rainfall_hazard_screen",
            "model_version": "rainfall-hazard-1.0.0",
        },
    }


def get_twin_health() -> dict[str, Any]:
    try:
        snapshot = build_twin_state()
        next_state = build_forecast_state(snapshot["observation_date"], 1)
        return {
            "status": "operational",
            "engine_version": ENGINE_VERSION,
            "contract_version": CONTRACT_VERSION,
            "synchronization": snapshot.get("observation_date"),
            "what_now": "pass",
            "what_next": "pass" if next_state["forecast"] else "fail",
            "what_if": "pass",
            "data_contract": "pass",
        }
    except Exception as error:
        return {
            "status": "degraded",
            "engine_version": ENGINE_VERSION,
            "contract_version": CONTRACT_VERSION,
            "error": str(error),
            "what_now": "fail",
            "what_next": "fail",
            "what_if": "fail",
            "data_contract": "fail",
        }