"""Climate layer registry and provider abstraction.

The UI can expose a stable set of climate layers without pretending that a
provider is connected. Each provider reports availability and provenance.
Large raster/NetCDF data stays outside the browser and is spatially filtered
by the eventual provider implementation.
"""
from __future__ import annotations

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
        "data_policy": "Unavailable providers return explicit NO_DATA/provider_required status; no synthetic climate values are generated.",
    }


def get_layer_status(layer: str, date: str) -> dict[str, Any]:
    key = layer.strip().lower()
    if key not in CLIMATE_LAYERS:
        raise ValueError(f"Unknown climate layer: {layer}")
    definition = CLIMATE_LAYERS[key]
    return {
        "layer": key,
        "title": definition["title"],
        "date": date,
        "status": definition["status"],
        "providers": definition["providers"],
        "endpoint": definition["endpoint"].replace("{date}", date),
        "data_available": definition["status"] == "connected",
        "scientific_note": "Provider-backed data only; this endpoint does not fabricate missing observations.",
    }


def unavailable_layer(layer: str, date: str) -> dict[str, Any]:
    status = get_layer_status(layer, date)
    status["status"] = "NO_DATA"
    status["data_available"] = False
    status["features"] = []
    return status
