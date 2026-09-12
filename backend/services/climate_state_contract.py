"""Canonical contract for the India Climate Digital Twin state."""

from __future__ import annotations

from typing import Any

CONTRACT_VERSION = "1.0.0"

VARIABLE_CATALOG: tuple[dict[str, Any], ...] = (
    {"id": "precipitation", "unit": "mm", "category": "atmosphere", "status": "active", "source": "IMD RF25"},
    {"id": "air_temperature_2m", "unit": "K", "category": "atmosphere", "status": "planned", "source": None},
    {"id": "relative_humidity", "unit": "%", "category": "atmosphere", "status": "planned", "source": None},
    {"id": "surface_pressure", "unit": "Pa", "category": "atmosphere", "status": "planned", "source": None},
    {"id": "wind_u_10m", "unit": "m s-1", "category": "atmosphere", "status": "planned", "source": None},
    {"id": "wind_v_10m", "unit": "m s-1", "category": "atmosphere", "status": "planned", "source": None},
    {"id": "soil_moisture", "unit": "m3 m-3", "category": "land", "status": "planned", "source": None},
    {"id": "vegetation_index", "unit": "1", "category": "earth_observation", "status": "planned", "source": None},
    {"id": "land_surface_temperature", "unit": "K", "category": "earth_observation", "status": "planned", "source": None},
    {"id": "rainfall_anomaly", "unit": "mm", "category": "derived", "status": "active", "source": "IMD RF25"},
    {"id": "temperature_anomaly", "unit": "K", "category": "derived", "status": "planned", "source": None},
    {"id": "extreme_precipitation_indicator", "unit": "1", "category": "derived", "status": "active", "source": "IMD RF25"},
    {"id": "hazard_score", "unit": "0-100", "category": "impact", "status": "active", "source": "rainfall hazard engine"},
)


def get_climate_state_contract() -> dict[str, Any]:
    active = [item for item in VARIABLE_CATALOG if item["status"] == "active"]
    planned = [item for item in VARIABLE_CATALOG if item["status"] == "planned"]
    return {
        "contract_version": CONTRACT_VERSION,
        "name": "India Climate Digital Twin State Contract",
        "representation": "synchronized, provenance-aware geospatial state",
        "active_variable_count": len(active),
        "planned_variable_count": len(planned),
        "variables": list(VARIABLE_CATALOG),
        "integrity_rules": [
            "Every active variable must have a validated source or documented derived-model provenance.",
            "Units and temporal/spatial conventions must be explicit.",
            "Missing variables must remain unavailable rather than being fabricated.",
            "Forecasts must record the input state hash and model version.",
            "Scenario outputs must identify which parameters are physically coupled.",
        ],
    }
