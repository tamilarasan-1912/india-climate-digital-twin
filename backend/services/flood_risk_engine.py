"""Flood-specific risk calculations for the Bharat Climate Twin.

Extends the generic risk engine with:
- Depth-damage curves for residential, commercial, industrial, agricultural
- Population exposure from flood extent grids
- Asset-level expected annual damage (EAD)
- Inundation duration and velocity considerations

All calculations are explicitly labeled with their scientific status.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from backend.services.risk_engine import _bounded


# Standard depth-damage curves (fractional damage at given depth in meters)
# Sources: FEMA, JRC, various Indian studies
DEPTH_DAMAGE_CURVES = {
    "residential": {
        "description": "Single-family residential structure + contents",
        "source": "FEMA / JRC composite for Indian context",
        "curve": [
            (0.0, 0.00),
            (0.15, 0.08),
            (0.30, 0.15),
            (0.45, 0.23),
            (0.60, 0.31),
            (0.90, 0.44),
            (1.20, 0.56),
            (1.50, 0.66),
            (1.80, 0.74),
            (2.10, 0.81),
            (2.40, 0.87),
            (2.70, 0.92),
            (3.00, 0.96),
            (5.00, 1.00),
        ],
    },
    "commercial": {
        "description": "Commercial/retail structure + contents",
        "source": "FEMA / JRC composite",
        "curve": [
            (0.0, 0.00),
            (0.15, 0.05),
            (0.30, 0.12),
            (0.45, 0.20),
            (0.60, 0.28),
            (0.90, 0.40),
            (1.20, 0.52),
            (1.50, 0.62),
            (1.80, 0.71),
            (2.10, 0.78),
            (2.40, 0.84),
            (2.70, 0.89),
            (3.00, 0.93),
            (5.00, 1.00),
        ],
    },
    "industrial": {
        "description": "Industrial/warehouse structure + equipment",
        "source": "FEMA / JRC composite",
        "curve": [
            (0.0, 0.00),
            (0.15, 0.03),
            (0.30, 0.08),
            (0.45, 0.15),
            (0.60, 0.23),
            (0.90, 0.35),
            (1.20, 0.47),
            (1.50, 0.58),
            (1.80, 0.67),
            (2.10, 0.75),
            (2.40, 0.81),
            (2.70, 0.87),
            (3.00, 0.92),
            (5.00, 1.00),
        ],
    },
    "agricultural": {
        "description": "Crop damage (rice/wheat typical)",
        "source": "Indian agricultural flood damage studies",
        "curve": [
            (0.0, 0.00),
            (0.15, 0.15),
            (0.30, 0.35),
            (0.45, 0.55),
            (0.60, 0.70),
            (0.90, 0.85),
            (1.20, 0.95),
            (1.50, 1.00),
        ],
    },
    "infrastructure": {
        "description": "Roads, bridges, utilities",
        "source": "Generic infrastructure",
        "curve": [
            (0.0, 0.00),
            (0.30, 0.10),
            (0.60, 0.25),
            (0.90, 0.45),
            (1.20, 0.65),
            (1.50, 0.80),
            (2.00, 0.95),
            (3.00, 1.00),
        ],
    },
}


def interpolate_damage(depth_m: float, asset_type: str) -> float:
    """Interpolate fractional damage from depth-damage curve.
    
    Args:
        depth_m: Flood depth in meters
        asset_type: One of DEPTH_DAMAGE_CURVES keys
    
    Returns:
        Fractional damage (0.0 to 1.0)
    """
    if asset_type not in DEPTH_DAMAGE_CURVES:
        asset_type = "residential"  # Default
    
    curve = DEPTH_DAMAGE_CURVES[asset_type]["curve"]
    depths = [c[0] for c in curve]
    damages = [c[1] for c in curve]
    
    if depth_m <= depths[0]:
        return 0.0
    if depth_m >= depths[-1]:
        return damages[-1]
    
    # Linear interpolation
    return float(np.interp(depth_m, depths, damages))


def velocity_factor(velocity_mps: float | None) -> float:
    """Adjustment factor for flow velocity.
    
    High velocity increases structural damage.
    Factor = 1.0 for v < 0.5 m/s, up to 1.5 for v > 2.0 m/s
    """
    if velocity_mps is None:
        return 1.0
    if velocity_mps <= 0.5:
        return 1.0
    if velocity_mps >= 2.0:
        return 1.5
    return 1.0 + 0.5 * (velocity_mps - 0.5) / 1.5


def duration_factor(duration_hours: float | None) -> float:
    """Adjustment factor for flood duration.
    
    Longer duration increases damage (mold, structural weakening).
    Factor = 1.0 for < 12h, up to 1.3 for > 72h
    """
    if duration_hours is None:
        return 1.0
    if duration_hours <= 12:
        return 1.0
    if duration_hours >= 72:
        return 1.3
    return 1.0 + 0.3 * (duration_hours - 12) / 60


def calculate_asset_flood_damage(
    *,
    asset_id: str,
    asset_type: str,
    replacement_value_inr: float,
    flood_depth_m: float,
    velocity_mps: float | None = None,
    duration_hours: float | None = None,
    content_value_ratio: float = 0.5,  # Contents typically 50% of structure
) -> dict[str, Any]:
    """Calculate flood damage for a single asset.
    
    Args:
        asset_id: Unique asset identifier
        asset_type: Asset type (residential, commercial, industrial, agricultural, infrastructure)
        replacement_value_inr: Structure replacement cost in INR
        flood_depth_m: Maximum flood depth at asset location (meters)
        velocity_mps: Flow velocity (m/s) if available
        duration_hours: Flood duration (hours) if available
        content_value_ratio: Contents value as fraction of structure value
    
    Returns:
        Damage assessment dictionary
    """
    if flood_depth_m < 0:
        flood_depth_m = 0.0
    
    # Base structural damage
    struct_damage_frac = interpolate_damage(flood_depth_m, asset_type)
    
    # Content damage (typically higher at same depth)
    content_damage_frac = min(1.0, struct_damage_frac * 1.3)
    
    # Velocity and duration adjustments
    v_factor = velocity_factor(velocity_mps)
    d_factor = duration_factor(duration_hours)
    combined_factor = min(v_factor * d_factor, 1.5)  # Cap combined effect
    
    adjusted_struct = min(struct_damage_frac * combined_factor, 1.0)
    adjusted_content = min(content_damage_frac * combined_factor, 1.0)
    
    # Calculate monetary damages
    struct_damage_inr = adjusted_struct * replacement_value_inr
    content_value_inr = replacement_value_inr * content_value_ratio
    content_damage_inr = adjusted_content * content_value_inr
    total_damage_inr = struct_damage_inr + content_damage_inr
    
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "flood_depth_m": flood_depth_m,
        "velocity_mps": velocity_mps,
        "duration_hours": duration_hours,
        "replacement_value_inr": replacement_value_inr,
        "content_value_inr": content_value_inr,
        "structural_damage_fraction": adjusted_struct,
        "content_damage_fraction": adjusted_content,
        "structural_damage_inr": struct_damage_inr,
        "content_damage_inr": content_damage_inr,
        "total_damage_inr": total_damage_inr,
        "damage_ratio": total_damage_inr / (replacement_value_inr + content_value_inr) if (replacement_value_inr + content_value_inr) > 0 else 0.0,
        "curve_source": DEPTH_DAMAGE_CURVES.get(asset_type, DEPTH_DAMAGE_CURVES["residential"])["source"],
        "scientific_status": "depth_damage_curve_based",
        "limitations": [
            "Depth-damage curves are generalized; site-specific curves needed for operational use",
            "Velocity and duration factors are approximate",
            "Does not account for contamination, debris, or sequential events",
            "Content value ratio is assumed; actual inventories required for accuracy",
        ],
    }


def calculate_population_exposure(
    *,
    flood_extent_grid: np.ndarray,  # Boolean or 0/1 grid
    population_grid: np.ndarray,    # Population count per grid cell
    flood_depth_grid: np.ndarray | None = None,  # Depth per cell (meters)
    velocity_grid: np.ndarray | None = None,     # Velocity per cell (m/s)
    hazard_threshold_depth: float = 0.15,  # Depth above which hazard exists
) -> dict[str, Any]:
    """Calculate population exposed to flooding.
    
    Args:
        flood_extent_grid: Boolean grid indicating flooded cells
        population_grid: Population count per grid cell
        flood_depth_grid: Optional depth grid for hazard classification
        velocity_grid: Optional velocity grid for hazard classification
        hazard_threshold_depth: Minimum depth to consider as flood hazard
    
    Returns:
        Population exposure assessment
    """
    # Exposed population (any flooding)
    exposed_mask = flood_extent_grid > 0
    total_population = float(np.nansum(population_grid))
    exposed_population = float(np.nansum(population_grid[exposed_mask]))
    
    # Classify by depth if available
    depth_classes = {
        "shallow": 0.0,
        "moderate": 0.0,
        "deep": 0.0,
        "very_deep": 0.0,
    }
    velocity_classes = {
        "low": 0.0,
        "moderate": 0.0,
        "high": 0.0,
    }
    
    if flood_depth_grid is not None:
        depth_shallow = (flood_depth_grid > hazard_threshold_depth) & (flood_depth_grid <= 0.5)
        depth_moderate = (flood_depth_grid > 0.5) & (flood_depth_grid <= 1.5)
        depth_deep = (flood_depth_grid > 1.5) & (flood_depth_grid <= 3.0)
        depth_very_deep = flood_depth_grid > 3.0
        
        depth_classes["shallow"] = float(np.nansum(population_grid[depth_shallow]))
        depth_classes["moderate"] = float(np.nansum(population_grid[depth_moderate]))
        depth_classes["deep"] = float(np.nansum(population_grid[depth_deep]))
        depth_classes["very_deep"] = float(np.nansum(population_grid[depth_very_deep]))
    
    if velocity_grid is not None:
        vel_low = (velocity_grid > 0) & (velocity_grid <= 0.5)
        vel_moderate = (velocity_grid > 0.5) & (velocity_grid <= 1.5)
        vel_high = velocity_grid > 1.5
        
        velocity_classes["low"] = float(np.nansum(population_grid[vel_low]))
        velocity_classes["moderate"] = float(np.nansum(population_grid[vel_moderate]))
        velocity_classes["high"] = float(np.nansum(population_grid[vel_high]))
    
    return {
        "total_population": total_population,
        "exposed_population": exposed_population,
        "exposure_fraction": exposed_population / total_population if total_population > 0 else 0.0,
        "depth_distribution": depth_classes,
        "velocity_distribution": velocity_classes,
        "scientific_status": "grid_based_exposure",
        "limitations": [
            "Population grid resolution may not capture building-level variation",
            "Assumes all population in flooded grid cell is exposed",
            "No evacuation or shelter-in-place modeling",
            "Grid source and vintage must be documented for auditability",
        ],
    }


def calculate_expected_annual_damage(
    asset_damages: list[dict[str, Any]],
    annual_exceedance_probabilities: list[float] | None = None,
) -> dict[str, Any]:
    """Calculate Expected Annual Damage (EAD) from multiple return period damages.
    
    Uses trapezoidal integration of the damage-probability curve.
    
    Args:
        asset_damages: List of damage assessments for different return periods
        annual_exceedance_probabilities: AEP for each scenario (e.g., [0.5, 0.1, 0.02, 0.01])
    
    Returns:
        EAD calculation results
    """
    if not asset_damages:
        return {"expected_annual_damage_inr": None, "status": "not_available"}
    
    if annual_exceedance_probabilities is None:
        # Default: assume 2, 10, 50, 100 year return periods
        annual_exceedance_probabilities = [0.5, 0.1, 0.02, 0.01]
    
    if len(asset_damages) != len(annual_exceedance_probabilities):
        return {
            "expected_annual_damage_inr": None,
            "status": "error",
            "error": "Number of damage scenarios must match number of AEPs",
        }
    
    # Sort by AEP (descending - highest probability first)
    sorted_pairs = sorted(zip(annual_exceedance_probabilities, asset_damages), key=lambda x: x[0], reverse=True)
    
    # Trapezoidal integration
    ead = 0.0
    for i in range(len(sorted_pairs) - 1):
        p1, d1 = sorted_pairs[i]
        p2, d2 = sorted_pairs[i + 1]
        damage1 = d1.get("total_damage_inr", 0)
        damage2 = d2.get("total_damage_inr", 0)
        ead += (damage1 + damage2) / 2 * (p1 - p2)
    
    return {
        "expected_annual_damage_inr": ead,
        "return_periods": [1/p for p in annual_exceedance_probabilities],
        "damages_by_return_period": [d.get("total_damage_inr", 0) for _, d in sorted_pairs],
        "status": "calculated",
        "method": "trapezoidal_integration",
        "limitations": [
            "Assumes damage-probability relationship is piecewise linear",
            "Return period scenarios must be hydraulically consistent",
            "Does not account for correlated failures or systemic effects",
        ],
    }


def assess_flood_risk_grid(
    *,
    hazard_grid: np.ndarray,          # Flood depth grid (meters)
    exposure_grid: np.ndarray,        # Population or asset value grid
    vulnerability_grid: np.ndarray | None = None,  # Vulnerability index 0-1
    velocity_grid: np.ndarray | None = None,
    cell_area_m2: float = 10000.0,    # Grid cell area (m²)
) -> dict[str, Any]:
    """Assess flood risk on a grid (for mapping).
    
    Args:
        hazard_grid: Flood depth (meters) per cell
        exposure_grid: Population or asset value per cell
        vulnerability_grid: Vulnerability index (0-1) per cell
        velocity_grid: Flow velocity (m/s) per cell
        cell_area_m2: Area of each grid cell
    
    Returns:
        Grid-based risk assessment
    """
    # Normalize hazard (depth-based)
    # 0.5m = moderate hazard, 2.0m = severe hazard
    hazard_norm = np.clip(hazard_grid / 2.0, 0, 1)
    
    # Normalize exposure
    exp_max = np.nanmax(exposure_grid) if np.any(np.isfinite(exposure_grid)) else 1.0
    exposure_norm = np.clip(exposure_grid / max(exp_max, 1e-6), 0, 1)
    
    # Vulnerability (default 0.5 if not provided)
    if vulnerability_grid is None:
        vulnerability_grid = np.full_like(hazard_grid, 0.5)
    vuln_norm = np.clip(vulnerability_grid, 0, 1)
    
    # Risk = Hazard × Exposure × Vulnerability
    risk_grid = hazard_norm * exposure_norm * vuln_norm
    
    # Apply velocity multiplier
    if velocity_grid is not None:
        vel_factor = np.ones_like(velocity_grid)
        vel_factor = np.where(velocity_grid > 0.5, 1.0 + 0.5 * np.minimum(velocity_grid / 2.0, 1.0), 1.0)
        risk_grid = np.clip(risk_grid * vel_factor, 0, 1)
    
    # Statistics
    valid = np.isfinite(risk_grid)
    if not np.any(valid):
        return {"risk_grid": risk_grid.tolist(), "statistics": {}, "status": "no_valid_cells"}
    
    return {
        "risk_grid": risk_grid[valid].tolist(),
        "statistics": {
            "mean_risk": float(np.nanmean(risk_grid)),
            "max_risk": float(np.nanmax(risk_grid)),
            "risk_area_m2": float(np.sum(valid) * cell_area_m2),
            "high_risk_cells": int(np.sum(risk_grid > 0.6)),
            "moderate_risk_cells": int(np.sum((risk_grid > 0.3) & (risk_grid <= 0.6))),
            "low_risk_cells": int(np.sum((risk_grid > 0.05) & (risk_grid <= 0.3))),
        },
        "hazard_summary": {
            "mean_depth_m": float(np.nanmean(hazard_grid[valid])),
            "max_depth_m": float(np.nanmax(hazard_grid[valid])),
            "flooded_area_m2": float(np.sum(hazard_grid > 0.05) * cell_area_m2),
        },
        "exposure_summary": {
            "total_exposure": float(np.nansum(exposure_grid)),
            "exposed_exposure": float(np.nansum(exposure_grid[hazard_grid > 0.05])),
        },
        "scientific_status": "grid_screening_risk",
        "limitations": [
            "Grid-based screening only; not a substitute for asset-level assessment",
            "Vulnerability defaults to 0.5 where not provided",
            "Cell size affects resolution; finer grids give more detail",
            "Requires validated hydraulic model outputs",
        ],
    }


def build_flood_risk_record(
    *,
    asset_id: str,
    location_id: str,
    asset_type: str,
    replacement_value_inr: float,
    flood_depth_m: float,
    velocity_mps: float | None = None,
    duration_hours: float | None = None,
    content_value_ratio: float = 0.5,
    population_exposed: int | None = None,
    probability: float | None = None,
    consequence_inr: float | None = None,
    model_version: str = "flood_risk_engine-1.0.0",
    assessment_time: str | None = None,
    data_quality_score: float | None = None,
    validation_status: str = "unvalidated",
) -> dict[str, Any]:
    """Build a complete flood risk record for an asset (compatible with risk contract).
    
    Returns:
        Risk record compatible with the platform risk contract
    """
    from datetime import datetime, timezone
    if assessment_time is None:
        assessment_time = datetime.now(timezone.utc).isoformat()
    
    # Calculate damage
    damage = calculate_asset_flood_damage(
        asset_id=asset_id,
        asset_type=asset_type,
        replacement_value_inr=replacement_value_inr,
        flood_depth_m=flood_depth_m,
        velocity_mps=velocity_mps,
        duration_hours=duration_hours,
        content_value_ratio=content_value_ratio,
    )
    
    # Hazard value = normalized depth (capped at 2m)
    hazard_value = _bounded(flood_depth_m / 2.0)
    
    # Exposure = normalized replacement value (relative to 10 Cr INR baseline)
    exposure_value = _bounded(replacement_value_inr / 100000000.0)
    
    # Vulnerability = damage ratio (fraction of total value damaged)
    vulnerability_value = damage["damage_ratio"]
    
    # Risk score
    from backend.services.risk_engine import combine_components
    risk_score, risk_status = combine_components(hazard_value, exposure_value, vulnerability_value)
    
    # Expected annual loss
    eal = None
    if probability is not None and consequence_inr is not None:
        from backend.services.risk_engine import expected_annual_loss
        eal = expected_annual_loss(probability, consequence_inr, vulnerability_value)
    
    return {
        "asset_id": asset_id,
        "location_id": location_id,
        "hazard": "flood",
        "hazard_value": hazard_value,
        "exposure_value": exposure_value,
        "vulnerability_value": vulnerability_value,
        "risk_score": risk_score,
        "risk_status": risk_status,
        "confidence": 0.6,  # Medium confidence for curve-based estimates
        "model_version": model_version,
        "assessment_time": assessment_time,
        "units": "depth_m",
        "data_quality_score": data_quality_score,
        "validation_status": validation_status,
        "limitations": damage["limitations"] + [
            "Risk score combines normalized components; not a direct probability",
            "Depth-damage curves require local calibration",
        ],
        "flood_specific": {
            "flood_depth_m": flood_depth_m,
            "velocity_mps": velocity_mps,
            "duration_hours": duration_hours,
            "asset_type": asset_type,
            "structural_damage_inr": damage["structural_damage_inr"],
            "content_damage_inr": damage["content_damage_inr"],
            "total_damage_inr": damage["total_damage_inr"],
            "damage_fraction": damage["damage_ratio"],
            "population_exposed": population_exposed,
            "expected_annual_loss_inr": eal,
        },
    }