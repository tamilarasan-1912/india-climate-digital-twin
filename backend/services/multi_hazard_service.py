"""Multi-hazard scoring from validated climate variables.

This is a transparent screening layer, not a replacement for hydrology,
coastal inundation, crop, fire or health impact models. A hazard is scored only
when its required variables are actually supplied.
"""
from __future__ import annotations

import math
from typing import Any


def _category(score: float) -> str:
    if score < 0.25: return "low"
    if score < 0.50: return "moderate"
    if score < 0.75: return "high"
    return "extreme"


def _norm(value: float | None, low: float, high: float) -> float | None:
    """Normalize a finite value; treat null and non-finite inputs as unavailable."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return max(0.0, min(1.0, (numeric - low) / (high - low)))


def calculate_hazards(state: dict[str, Any]) -> dict[str, Any]:
    vars = state.get("twin_state", {}).get("variables", {})
    rain = vars.get("rainfall", {}).get("statistics", {}).get("mean")
    temp = vars.get("temperature", {}).get("statistics", {}).get("mean")
    wind = vars.get("wind", {}).get("statistics", {}).get("mean")
    humidity = vars.get("humidity", {}).get("statistics", {}).get("mean")

    hazards: dict[str, Any] = {}
    rain_score = _norm(rain, 20, 200)
    if rain_score is not None:
        hazards["extreme_rainfall"] = {"status": "available", "score": rain_score, "category": _category(rain_score), "drivers": ["rainfall"]}
        hazards["rainfall_flood_screening"] = {"status": "available", "score": rain_score, "category": _category(rain_score), "drivers": ["rainfall"], "warning": "screening only; no runoff/inundation model"}
    else:
        hazards["extreme_rainfall"] = {"status": "no_data"}
        hazards["rainfall_flood_screening"] = {"status": "no_data"}

    temp_score = _norm(temp, 30, 48)
    if temp_score is not None:
        hazards["heat"] = {"status": "available", "score": temp_score, "category": _category(temp_score), "drivers": ["temperature"]}
    else:
        hazards["heat"] = {"status": "no_data"}

    wind_score = _norm(wind, 8, 35)
    if wind_score is not None:
        hazards["wind"] = {"status": "available", "score": wind_score, "category": _category(wind_score), "drivers": ["wind"]}
    else:
        hazards["wind"] = {"status": "no_data"}

    temperature_heat_score = _norm(temp, 28, 45)
    humidity_score = _norm(humidity, 50, 100)
    if temperature_heat_score is not None and humidity_score is not None:
        # Screening indicator only; not a certified heat-index implementation.
        score = max(0.0, min(1.0, (temperature_heat_score * 0.7) + (humidity_score * 0.3)))
        hazards["heat_stress_screening"] = {"status": "available", "score": score, "category": _category(score), "drivers": ["temperature", "humidity"], "warning": "screening indicator; not a clinical heat-index product"}
    else:
        hazards["heat_stress_screening"] = {"status": "no_data"}

    available_scores = [v["score"] for v in hazards.values() if v.get("score") is not None]
    return {
        "scope": "India",
        "status": "available" if available_scores else "no_data",
        "hazards": hazards,
        "overall_screening": max(available_scores) if available_scores else None,
        "overall_category": _category(max(available_scores)) if available_scores else "no_data",
        "scientific_boundary": "screening layer; physical impact models must be added before operational flood, drought, coastal or sectoral claims",
    }
