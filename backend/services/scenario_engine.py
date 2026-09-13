"""Scenario engine with explicit physical-coupling semantics."""
from __future__ import annotations

from typing import Any

from backend.models.domain_models import Scenario

SUPPORTED_HORIZONS = {2030, 2050, 2100}


def build_scenario(
    *,
    scenario_id: str,
    name: str,
    horizon_year: int | None = None,
    climate_scenario: str | None = None,
    precipitation_delta_pct: float = 0,
    temperature_delta_c: float = 0,
    sea_level_rise_m: float = 0,
) -> dict[str, Any]:
    """Create a scenario and explicitly mark uncoupled inputs.

    Until a validated hydrology/coastal model is connected, perturbations are
    sensitivity parameters rather than claims of physical simulation.
    """
    if horizon_year is not None and horizon_year not in SUPPORTED_HORIZONS:
        raise ValueError("Supported scenario horizons are 2030, 2050 and 2100")

    coupled: list[str] = []
    uncoupled: list[str] = []
    if precipitation_delta_pct:
        # The current rainfall hazard engine supports a mathematical sensitivity
        # experiment, not a hydraulic flood simulation.
        coupled.append("rainfall_hazard_sensitivity")
    if temperature_delta_c:
        coupled.append("temperature_hazard_sensitivity")
    if sea_level_rise_m:
        uncoupled.append("coastal_inundation")

    scenario = Scenario(
        scenario_id=scenario_id,
        name=name,
        horizon_year=horizon_year,
        climate_scenario=climate_scenario,
        precipitation_delta_pct=precipitation_delta_pct,
        temperature_delta_c=temperature_delta_c,
        sea_level_rise_m=sea_level_rise_m,
        coupled_models=coupled,
        uncoupled_parameters=uncoupled,
    )
    return {
        **scenario.model_dump(),
        "scientific_status": "sensitivity_experiment",
        "physical_simulation_available": False,
        "limitations": [
            "Flood depth requires terrain, drainage and validated hydraulic/hydrologic models.",
            "Sea-level rise requires bathymetry/elevation, surge and coastal inundation modeling.",
        ],
    }
