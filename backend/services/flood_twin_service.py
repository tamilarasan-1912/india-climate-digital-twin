"""Hydrologic/hydraulic flood-twin integration boundary.

The service does not fabricate flood depths. It defines the production adapter
contract for terrain, rainfall-runoff and 2D hydraulic engines such as HEC-RAS.
A validated model result can be ingested into the common risk contract later.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

FLOOD_ENGINE_VERSION = "0.1.0"


def get_flood_twin_status() -> dict[str, Any]:
    hec_ras_path = os.getenv("HECRAS_EXECUTABLE")
    terrain_root = Path(os.getenv("FLOOD_TERRAIN_ROOT", "data/flood/terrain"))
    return {
        "engine": "HEC-RAS-compatible hydraulic adapter",
        "adapter_version": FLOOD_ENGINE_VERSION,
        "hec_ras_configured": bool(hec_ras_path),
        "terrain_available": terrain_root.exists(),
        "required_inputs": [
            "validated DEM/terrain",
            "land-cover or Manning-n zones",
            "rainfall forcing",
            "boundary conditions",
            "drainage/river geometry",
            "calibration/validation observations",
        ],
        "outputs": [
            "flood_depth_m",
            "water_surface_elevation_m",
            "velocity_mps",
            "inundation_extent",
            "arrival_time",
        ],
        "status": "adapter_ready" if hec_ras_path else "blocked_until_hydraulic_model_is_configured",
        "scientific_guardrail": "No flood depth or inundation probability is generated without a validated hydraulic model run.",
    }


def build_flood_run_manifest(
    *,
    scenario_id: str,
    rainfall_asset_uri: str,
    terrain_asset_uri: str,
    geometry_asset_uri: str,
    boundary_condition_uri: str | None = None,
) -> dict[str, Any]:
    """Create a reproducible hydraulic-run manifest for an external solver."""
    required = {
        "rainfall_asset_uri": rainfall_asset_uri,
        "terrain_asset_uri": terrain_asset_uri,
        "geometry_asset_uri": geometry_asset_uri,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise ValueError("Missing flood model inputs: " + ", ".join(missing))
    return {
        "scenario_id": scenario_id,
        "solver": "HEC-RAS-2D",
        "solver_version": os.getenv("HECRAS_VERSION", "external-config"),
        "inputs": {**required, "boundary_condition_uri": boundary_condition_uri},
        "validation_required": True,
        "output_contract": ["depth_m", "velocity_mps", "extent_geojson", "arrival_time_s"],
    }
