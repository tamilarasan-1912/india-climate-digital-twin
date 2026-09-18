"""Operational God's-Eye services: timeline, event objects and data freshness.

The service composes existing provider-backed observations and forecasts. It never
turns missing observations into synthetic values.
"""
from __future__ import annotations

from datetime import date as date_type, timedelta
from typing import Any

from backend.services.digital_twin_service import get_historical_rainfall, get_baseline_forecast
from backend.services.extreme_event_service import get_extreme_rainfall_geojson, get_extreme_event_summary
from backend.services.climate_layer_service import get_climate_layer_catalog, get_layer_status


def _iso(value: str) -> str:
    date_type.fromisoformat(value)
    return value


def build_gods_eye_timeline(start: str, end: str, forecast_horizon: int = 7) -> dict[str, Any]:
    _iso(start)
    _iso(end)
    if start > end:
        raise ValueError("start must be on or before end")
    history = get_historical_rainfall(start, end, 5000)
    forecast = get_baseline_forecast(forecast_horizon)
    return {
        "contract": "india-climate-timeline/v1",
        "history": {
            "provider": history.get("provider"),
            "unit": history.get("unit"),
            "count": history.get("count", 0),
            "series": history.get("series", []),
        },
        "forecast": forecast,
        "boundaries": {"start": start, "end": end},
        "policy": "Historical values are provider-backed; forecast values are explicitly labeled model output.",
    }


def build_gods_eye_events(date: str) -> dict[str, Any]:
    _iso(date)
    geojson = get_extreme_rainfall_geojson(date)
    summary = get_extreme_event_summary(date)
    objects = []
    for index, feature in enumerate(geojson.get("features", [])):
        props = feature.get("properties", {})
        objects.append({
            "id": f"rainfall-{date}-{index + 1:04d}",
            "type": "extreme_rainfall",
            "geometry": feature.get("geometry"),
            "time": date,
            "intensity": props.get("rainfall_mm"),
            "category": props.get("category") or props.get("rainfall_category"),
            "source": "IMD-derived event detector",
            "properties": props,
        })
    return {
        "contract": "india-climate-events/v1",
        "date": date,
        "summary": summary.get("summary", summary),
        "events": objects,
        "count": len(objects),
        "policy": "Events are derived only from the connected rainfall dataset and detector.",
    }


def build_gods_eye_operations(date: str) -> dict[str, Any]:
    _iso(date)
    layers = get_climate_layer_catalog()["layers"]
    freshness = []
    for key, definition in layers.items():
        status = get_layer_status(key, date)
        freshness.append({
            "layer": key,
            "title": definition["title"],
            "provider": ", ".join(definition["providers"]),
            "status": status["status"],
            "data_available": status["data_available"],
            "observation_time": date if status["data_available"] else None,
            "freshness": "dataset-date" if status["data_available"] else "unknown",
            "uncertainty": "not calibrated" if key in {"rainfall", "risk", "events"} else "not available",
        })
    return {
        "contract": "india-climate-operations/v1",
        "date": date,
        "layers": freshness,
        "system": {
            "mode": "observation",
            "data_policy": "No fabricated observations; unavailable or unvalidated providers remain explicit.",
        },
    }
