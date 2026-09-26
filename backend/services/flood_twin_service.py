"""Hydrologic/hydraulic flood-twin integration boundary.

The service does not fabricate flood depths. It defines the production adapter
contract for terrain, rainfall-runoff and 2D hydraulic engines such as HEC-RAS.
A validated model result can be ingested into the common risk contract later.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
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


def build_gr4j_to_hecras_boundary(
    *,
    gr4j_result: dict[str, Any],
    basin_id: str,
    scenario_id: str,
    output_dir: str | Path = "backend/data/flood/boundary_conditions",
) -> dict[str, Any]:
    """Create HEC-RAS boundary condition files from GR4J discharge output.
    
    Converts GR4J discharge time series (m³/s) to HEC-RAS compatible format.
    
    Args:
        gr4j_result: Output from run_gr4j_simulation
        basin_id: Basin identifier
        scenario_id: Scenario identifier
        output_dir: Directory to write boundary condition files
    
    Returns:
        Dictionary with boundary condition file paths and metadata
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    dates = gr4j_result["dates"]
    discharge_m3s = gr4j_result["discharge_m3s"]
    
    # Create HEC-RAS boundary condition file (BC file format)
    # Format: Date/Time, Flow (m³/s) for upstream boundary
    bc_file = output_path / f"{scenario_id}_upstream_bc.bc"
    with open(bc_file, "w") as f:
        f.write("HEC-RAS Boundary Condition File\n")
        f.write(f"Scenario: {scenario_id}\n")
        f.write(f"Basin: {basin_id}\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Source: GR4J rainfall-runoff simulation\n")
        f.write(f"Variables: Date, Discharge_m3s\n")
        f.write("Date,Discharge_m3s\n")
        for date_str, q in zip(dates, discharge_m3s):
            f.write(f"{date_str}T00:00:00,{q:.2f}\n")
    
    # Create JSON version for programmatic access
    bc_json = output_path / f"{scenario_id}_upstream_bc.json"
    with open(bc_json, "w") as f:
        json.dump({
            "scenario_id": scenario_id,
            "basin_id": basin_id,
            "source": "GR4J",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "variables": ["discharge_m3s"],
            "timeseries": [
                {"date": d, "discharge_m3s": q}
                for d, q in zip(dates, discharge_m3s)
            ],
        }, f, indent=2)
    
    return {
        "scenario_id": scenario_id,
        "basin_id": basin_id,
        "boundary_condition_files": {
            "hecras_bc": str(bc_file),
            "json": str(bc_json),
        },
        "time_range": {"start": dates[0], "end": dates[-1]},
        "discharge_range_m3s": {"min": min(discharge_m3s), "max": max(discharge_m3s)},
        "note": "Upstream boundary condition for HEC-RAS 2D. Downstream boundary (stage-discharge or normal depth) must be provided separately.",
    }


def build_hecras_geometry_manifest(
    *,
    basin_id: str,
    scenario_id: str,
    river_centerline_path: str,
    cross_sections_path: str | None = None,
    output_dir: str | Path = "backend/data/flood/geometry",
) -> dict[str, Any]:
    """Create HEC-RAS geometry input manifest.
    
    Args:
        basin_id: Basin identifier
        scenario_id: Scenario identifier
        river_centerline_path: Path to river centerline shapefile/GeoJSON
        cross_sections_path: Path to cross sections shapefile/GeoJSON (optional)
        output_dir: Directory to write geometry manifest
    
    Returns:
        Dictionary with geometry file references
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    geometry_manifest = output_path / f"{scenario_id}_geometry_manifest.json"
    with open(geometry_manifest, "w") as f:
        json.dump({
            "scenario_id": scenario_id,
            "basin_id": basin_id,
            "river_centerline": river_centerline_path,
            "cross_sections": cross_sections_path,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, f, indent=2)
    
    return {
        "scenario_id": scenario_id,
        "basin_id": basin_id,
        "geometry_manifest": str(geometry_manifest),
        "required_for_hecras": [
            "river_centerline (mandatory)",
            "cross_sections (recommended for 1D/2D coupling)",
            "bank_lines (for 2D mesh generation)",
        ],
    }


def build_full_hydro_hydraulic_manifest(
    *,
    gr4j_result: dict[str, Any],
    basin_id: str,
    scenario_id: str,
    terrain_asset_uri: str,
    river_centerline_path: str,
    cross_sections_path: str | None = None,
    landcover_asset_uri: str | None = None,
    downstream_bc_type: str = "normal_depth",
    downstream_bc_value: float | None = None,
) -> dict[str, Any]:
    """Build complete manifest for GR4J → HEC-RAS coupled simulation.
    
    This creates all input files needed for a full hydro-hydraulic run.
    
    Returns:
        Complete manifest with all input files and HEC-RAS project structure
    """
    # Build boundary conditions from GR4J
    bc_result = build_gr4j_to_hecras_boundary(
        gr4j_result=gr4j_result,
        basin_id=basin_id,
        scenario_id=scenario_id,
    )
    
    # Build geometry manifest
    geom_result = build_hecras_geometry_manifest(
        basin_id=basin_id,
        scenario_id=scenario_id,
        river_centerline_path=river_centerline_path,
        cross_sections_path=cross_sections_path,
    )
    
    # Build full manifest
    full_manifest = {
        "scenario_id": scenario_id,
        "basin_id": basin_id,
        "coupling": "GR4J_rainfall_runoff_to_HECRAS_2D",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hydrology": {
            "model": "GR4J",
            "model_version": "1.0.0",
            "result_summary": {
                "period": f"{gr4j_result['dates'][0]} to {gr4j_result['dates'][-1]}",
                "mean_discharge_m3s": sum(gr4j_result["discharge_m3s"]) / len(gr4j_result["discharge_m3s"]),
                "peak_discharge_m3s": max(gr4j_result["discharge_m3s"]),
            },
            "boundary_conditions": bc_result,
        },
        "hydraulics": {
            "model": "HEC-RAS-2D",
            "geometry": geom_result,
            "terrain": terrain_asset_uri,
            "landcover": landcover_asset_uri,
            "downstream_boundary": {
                "type": downstream_bc_type,
                "value": downstream_bc_value,
            },
        },
        "outputs_requested": [
            "depth_m",
            "water_surface_elevation_m",
            "velocity_mps",
            "inundation_extent_geojson",
            "arrival_time_s",
        ],
        "validation_required": True,
        "status": "manifest_generated",
        "note": "This manifest defines all inputs for HEC-RAS. The hydraulic model must be executed externally. Results can be ingested via /api/v1/simulation/jobs/{job_id}/flood-result",
    }
    
    return full_manifest
