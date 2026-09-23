"""Climate layer registry and provider availability contracts.

The registry describes which scientific layers the product understands. It is
not, by itself, proof that a value exists for a requested date. Date-scoped
status is resolved from the connected rainfall dataset or the provider
validation boundary so the UI can distinguish capability, configuration, and
actual data availability.
"""
from __future__ import annotations

from datetime import date as date_type
from typing import Any


CLIMATE_LAYERS: dict[str, dict[str, Any]] = {
    "rainfall": {
        "title": "Rainfall",
        "variables": ["precipitation"],
        "providers": ["IMD"],
        "status": "connected",
        "endpoint": "/api/rainfall/grid/{date}",
        "visualization": "point_grid",
    },
    "temperature": {
        "title": "Temperature",
        "variables": ["air_temperature_max", "air_temperature_min", "air_temperature_mean"],
        "providers": ["IMD", "ERA5"],
        "status": "provider_required",
        "endpoint": "/api/climate/temperature/{date}",
        "visualization": "raster",
    },
    "lst": {
        "title": "Land Surface Temperature",
        "variables": ["land_surface_temperature"],
        "providers": ["ISRO/MOSDAC", "MODIS", "Landsat"],
        "status": "provider_required",
        "endpoint": "/api/climate/lst/{date}",
        "visualization": "raster",
    },
    "sst": {
        "title": "Sea Surface Temperature",
        "variables": ["sea_surface_temperature"],
        "providers": ["ISRO/MOSDAC", "ERA5"],
        "status": "provider_required",
        "endpoint": "/api/climate/sst/{date}",
        "visualization": "raster",
    },
    "anomalies": {
        "title": "Climate Anomalies",
        "variables": ["precipitation_anomaly", "temperature_anomaly"],
        "providers": ["validated climatology + observation source"],
        "status": "partial",
        "endpoint": "/api/climate/anomalies/{date}",
        "visualization": "raster",
    },
    "risk": {
        "title": "Climate Risk",
        "variables": ["hazard", "exposure", "vulnerability"],
        "providers": ["risk engine"],
        "status": "connected",
        "endpoint": "/api/risk/grid/{date}",
        "visualization": "point_grid",
    },
    "events": {
        "title": "Climate Events",
        "variables": ["extreme_rainfall"],
        "providers": ["IMD-derived event detector"],
        "status": "connected",
        "endpoint": "/api/extreme-events/rainfall/geojson/{date}",
        "visualization": "event_points",
    },
}


def get_climate_layer_catalog() -> dict[str, Any]:
    return {
        "scope": "India",
        "layers": CLIMATE_LAYERS,
        "status_semantics": {
            "connected": "The implemented service can serve validated data when the requested date is covered.",
            "provider_required": "No validated provider adapter is connected.",
            "partial": "The contract exists but a required baseline or observation source is missing.",
            "configured": "A URL exists, but it has not passed provider validation.",
            "NO_DATA": "The service is known but no value is available for this request.",
        },
        "data_policy": "Unavailable providers return explicit NO_DATA/provider_required status; no synthetic climate values are generated.",
    }


def _validate_date(value: str) -> str:
    try:
        return date_type.fromisoformat(value).isoformat()
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid climate date: {value}") from error


def _rainfall_available(date: str) -> bool:
    # Keep the registry import-light. The date check is intentionally backed by
    # the actual IMD service rather than the existence of a file alone.
    from backend.services.rainfall_service import get_daily_statistics

    try:
        get_daily_statistics(date)
    except (FileNotFoundError, ValueError):
        return False
    return True


def get_layer_status(layer: str, date: str) -> dict[str, Any]:
    key = layer.strip().lower()
    if key not in CLIMATE_LAYERS:
        raise ValueError(f"Unknown climate layer: {layer}")
    requested_date = _validate_date(date)
    definition = CLIMATE_LAYERS[key]

    if key in {"rainfall", "risk", "events"}:
        available = _rainfall_available(requested_date)
        status = "CONNECTED" if available else "NO_DATA"
        note = (
            "Validated IMD rainfall data is available for this date."
            if available
            else "The IMD rainfall dataset does not cover this date or is unavailable."
        )
    else:
        from backend.services.climate_provider import provider_config

        config = provider_config(key)
        available = False
        if config["url_configured"]:
            status = "CONFIGURED (VALIDATION PENDING)"
            note = "A provider URL is configured but this status endpoint does not promote it without a validated data response."
        else:
            status = "PROVIDER REQUIRED"
            note = "No validated provider URL is configured for this layer."

    return {
        "layer": key,
        "title": definition["title"],
        "date": requested_date,
        "status": status,
        "providers": definition["providers"],
        "endpoint": definition["endpoint"].replace("{date}", requested_date),
        "data_available": available,
        "scientific_note": note,
        "data_policy": "Provider-backed data only; this endpoint does not fabricate missing observations.",
    }


def unavailable_layer(layer: str, date: str) -> dict[str, Any]:
    status = get_layer_status(layer, date)
    status["status"] = "NO_DATA"
    status["data_available"] = False
    status["features"] = []
    return status
