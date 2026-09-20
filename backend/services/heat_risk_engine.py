"""Heat-risk screening using supplied temperature, humidity and exposure inputs.

This is a transparent screening layer, not a medical or operational heat-health
forecast. A validated Indian heat-health model can replace the scoring function
without changing the API boundary.
"""
from __future__ import annotations

from typing import Any


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _heat_index_celsius(temperature_c: float, relative_humidity_pct: float) -> float:
    """NOAA/Rothfusz heat-index approximation, converted to Celsius."""
    t_f = temperature_c * 9.0 / 5.0 + 32.0
    rh = relative_humidity_pct
    if t_f < 80.0 or rh < 40.0:
        return temperature_c
    hi_f = (
        -42.379
        + 2.04901523 * t_f
        + 10.14333127 * rh
        - 0.22475541 * t_f * rh
        - 0.00683783 * t_f * t_f
        - 0.05481717 * rh * rh
        + 0.00122874 * t_f * t_f * rh
        + 0.00085282 * t_f * rh * rh
        - 0.00000199 * t_f * t_f * rh * rh
    )
    return (hi_f - 32.0) * 5.0 / 9.0


def assess_heat_risk(
    *,
    temperature_c: float,
    relative_humidity_pct: float,
    exposure_index: float | None = None,
    confidence: float | None = None,
    model_version: str = "heat-screening-1.0.0",
) -> dict[str, Any]:
    if not 0 <= relative_humidity_pct <= 100:
        raise ValueError("relative_humidity_pct must be between 0 and 100")
    if exposure_index is None:
        return {
            "status": "not_available",
            "risk_score": None,
            "model_version": model_version,
            "limitations": ["Exposure index is required; the engine does not infer population exposure."],
        }

    heat_index = _heat_index_celsius(temperature_c, relative_humidity_pct)
    thermal_component = _bounded((heat_index - 27.0) / 18.0)
    risk_score = thermal_component * _bounded(exposure_index)
    category = "low" if risk_score < 0.25 else "moderate" if risk_score < 0.5 else "high" if risk_score < 0.75 else "very_high"
    return {
        "status": "screening_only",
        "risk_score": risk_score,
        "category": category,
        "inputs": {
            "temperature_c": temperature_c,
            "relative_humidity_pct": relative_humidity_pct,
            "exposure_index": exposure_index,
        },
        "derived": {"heat_index_c": heat_index},
        "confidence": confidence,
        "model_version": model_version,
        "validation_status": "unvalidated",
        "limitations": [
            "Rothfusz heat index is a screening metric and is not an Indian heat-health mortality model.",
            "Operational alerts require validated local thresholds, forecasts and health-agency rules.",
        ],
    }
