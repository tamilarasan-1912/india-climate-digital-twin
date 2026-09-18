"""Configurable external climate-data provider boundary.

The application never treats a configured URL as proof that data is valid.
Providers must return application-compatible JSON/GeoJSON and should be
validated by a dataset-specific adapter before being promoted to connected
status. This keeps the UI/API extensible without fabricating climate values.
"""
from __future__ import annotations

import os
from typing import Any

from backend.services.climate_layer_service import CLIMATE_LAYERS


ENV_BY_LAYER = {
    "temperature": "CLIMATE_PROVIDER_TEMPERATURE_URL",
    "lst": "CLIMATE_PROVIDER_LST_URL",
    "sst": "CLIMATE_PROVIDER_SST_URL",
    "anomalies": "CLIMATE_PROVIDER_ANOMALIES_URL",
}


def provider_config(layer: str) -> dict[str, Any]:
    key = layer.strip().lower()
    if key not in CLIMATE_LAYERS:
        raise ValueError(f"Unknown climate layer: {layer}")
    env_name = ENV_BY_LAYER.get(key)
    url = os.getenv(env_name, "").strip() if env_name else ""
    return {
        "layer": key,
        "configured": bool(url),
        "env_var": env_name,
        "url_configured": bool(url),
        "status": "configured" if url else "provider_required",
        "note": (
            "Configured endpoint must be validated by a source-specific adapter "
            "before it is treated as connected."
        ),
    }


def get_provider_registry() -> dict[str, Any]:
    return {
        "providers": {
            layer: provider_config(layer)
            for layer in ("rainfall", "temperature", "lst", "sst", "anomalies")
        },
        "policy": "Configuration alone never creates climate observations or forecasts.",
    }
