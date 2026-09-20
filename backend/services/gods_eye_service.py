"""God's-Eye aggregation contract for the India Climate Digital Twin.

This service is intentionally an orchestration layer: it combines existing
provider-backed contracts into one compact payload for the geospatial console.
It never synthesizes missing climate observations.
"""
from __future__ import annotations

from typing import Any

from backend.services.climate_layer_service import get_climate_layer_catalog
from backend.services.climate_provider_runtime import get_provider_layer
from backend.services.rainfall_service import get_india_daily_summary, get_rainfall_grid
from backend.services.extreme_event_service import get_extreme_event_summary, get_extreme_rainfall_geojson
from backend.services.climate_risk_service import get_climate_risk_summary, get_climate_risk_grid
from backend.services.india_hierarchy_service import get_india_hierarchy


def build_gods_eye_state(date: str) -> dict[str, Any]:
    """Return the map/HUD state needed by the God's-Eye frontend."""
    def safe(fn, *args):
        try:
            return fn(*args)
        except Exception as exc:
            return {"status": "NO_DATA", "error": str(exc)}

    layers = get_climate_layer_catalog()["layers"]
    return {
        "contract": "india-climate-gods-eye/v1",
        "scope": "India",
        "observation_date": date,
        "camera": {
            "center": [78.9629, 20.5937],
            "fit_bounds": [[68.0, 6.0], [97.0, 36.0]],
            "min_zoom": 3,
            "max_zoom": 10,
        },
        "layers": layers,
        "observations": {
            "rainfall": safe(get_india_daily_summary, date),
            "risk": safe(get_climate_risk_summary, date),
            "events": safe(get_extreme_event_summary, date),
        },
        "map_sources": {
            "rainfall": safe(get_rainfall_grid, date),
            "risk": safe(get_climate_risk_grid, date),
            "events": safe(get_extreme_rainfall_geojson, date),
        },
        "geography": {
            "administrative": "/data/india/india-states.geojson",
            "hierarchy": safe(get_india_hierarchy),
        },
        "data_policy": (
            "Provider-backed observations only. Missing providers are represented "
            "as NO_DATA/provider_required; no synthetic climate values are generated."
        ),
    }


def get_gods_eye_layer(layer: str, date: str) -> dict[str, Any]:
    key = layer.strip().lower()
    if key == "rainfall":
        return get_rainfall_grid(date)
    if key == "risk":
        return get_climate_risk_grid(date)
    if key == "events":
        return get_extreme_rainfall_geojson(date)
    if key in {"temperature", "lst", "sst", "anomalies"}:
        # Route through the validated provider runtime so a configured (and
        # responding) adapter can supply the layer. When nothing is connected
        # the runtime returns an explicit NO_DATA payload.
        return get_provider_layer(key, date)
    raise ValueError(f"Unknown God's-Eye climate layer: {layer}")
