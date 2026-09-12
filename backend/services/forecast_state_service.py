"""Forecast-state integration for the India Climate Digital Twin.

This module converts an actual Prithvi-WxC rollout tensor into a provenance-
aware forecast state. It never invents channels: only channels explicitly
mapped from the model output are exposed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence

import numpy as np

from backend.services.multi_variable_twin_service import build_state_envelope

# The first 20 channels are the surface variables in the official Prithvi-WxC
# ordering. Vertical channels follow as variable x 14 levels.
SURFACE_CHANNELS = (
    "EFLUX", "GWETROOT", "HFLUX", "LAI", "LWGAB", "LWGEM", "LWTUP",
    "PS", "QV2M", "SLP", "SWGNT", "SWTNT", "T2M", "TQI", "TQL",
    "TQV", "TS", "U10M", "V10M", "Z0M",
)

# Contract variables currently supported by the twin. PRECTOT is intentionally
# not mapped here because the rollout checkpoint's surface channel contract
# does not contain it.
MODEL_TO_TWIN = {
    "T2M": ("air_temperature_2m", "K"),
    "QV2M": ("specific_humidity_2m", "kg/kg"),
    "PS": ("surface_pressure", "Pa"),
    "SLP": ("sea_level_pressure", "Pa"),
    "U10M": ("wind_u_10m", "m/s"),
    "V10M": ("wind_v_10m", "m/s"),
    "LAI": ("leaf_area_index", "1"),
    "TS": ("land_surface_temperature", "K"),
}


def _as_array(output: Any) -> np.ndarray:
    if hasattr(output, "detach"):
        output = output.detach().cpu().numpy()
    array = np.asarray(output)
    if not np.isfinite(array).all():
        raise ValueError("Prithvi forecast contains NaN or infinite values")
    return array


def _surface_field(output: np.ndarray, channel: int) -> np.ndarray:
    """Extract a surface field from [B,T,C,H,W] or [B,C,H,W] output."""
    if output.ndim == 5:
        return output[0, -1, channel]
    if output.ndim == 4:
        return output[0, channel]
    if output.ndim == 3:
        return output[channel]
    raise ValueError(f"Unsupported Prithvi output shape: {tuple(output.shape)}")


def build_forecast_state(
    output: Any,
    *,
    forecast_time: str,
    input_time: str,
    source_state_hash: str | None = None,
    model_name: str = "Prithvi-WxC-1.0-2300M-rollout",
    model_version: str = "1.0.0",
    lead_time_hours: int = 6,
) -> dict[str, Any]:
    """Build a Digital Twin forecast envelope from a genuine model output."""
    tensor = _as_array(output)
    variables: dict[str, Mapping[str, Any]] = {}

    for index, model_name_key in enumerate(SURFACE_CHANNELS):
        mapping = MODEL_TO_TWIN.get(model_name_key)
        if mapping is None:
            continue
        twin_id, unit = mapping
        field = _surface_field(tensor, index)
        variables[twin_id] = {
            "value": {
                "minimum": float(np.min(field)),
                "mean": float(np.mean(field)),
                "maximum": float(np.max(field)),
                "grid_shape": list(field.shape),
            },
            "unit": unit,
            "source": "Prithvi-WxC rollout forecast",
            "model_channel": model_name_key,
            "lead_time_hours": lead_time_hours,
        }

    envelope = build_state_envelope(
        observation_time=forecast_time,
        variables=variables,
        source_state_hash=source_state_hash,
        model={
            "name": model_name,
            "version": model_version,
            "input_time": input_time,
            "forecast_time": forecast_time,
            "lead_time_hours": lead_time_hours,
            "output_shape": list(tensor.shape),
        },
    )
    envelope["forecast"] = True
    envelope["generated_at"] = datetime.now(timezone.utc).isoformat()
    return envelope


def build_hazard_summary(forecast_state: Mapping[str, Any]) -> dict[str, Any]:
    """Derive transparent hazard indicators only from available forecast fields."""
    values = forecast_state.get("variables", {})
    hazards: dict[str, Any] = {}

    temp = values.get("air_temperature_2m")
    if temp:
        mean_k = float(temp["value"]["mean"])
        hazards["heat"] = {
            "indicator": "2m air temperature",
            "mean_temperature_c": mean_k - 273.15,
            "status": "screening_only",
        }

    u = values.get("wind_u_10m")
    v = values.get("wind_v_10m")
    if u and v:
        speed = float(np.hypot(float(u["value"]["mean"]), float(v["value"]["mean"])))
        hazards["wind"] = {
            "indicator": "10m wind speed",
            "mean_wind_speed_mps": speed,
            "status": "screening_only",
        }

    if "air_temperature_2m" not in values:
        hazards["heat"] = {"status": "not_available"}
    if "wind_u_10m" not in values or "wind_v_10m" not in values:
        hazards["wind"] = {"status": "not_available"}

    hazards["precipitation"] = {
        "status": "not_available",
        "reason": "The current official Prithvi-WxC surface channel contract does not expose PRECTOT as a rollout surface channel.",
    }

    return {
        "hazards": hazards,
        "scientific_status": "screening indicators; not calibrated impact probabilities",
        "population_impact": "not computed",
    }
