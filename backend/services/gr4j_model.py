"""GR4J Rainfall-Runoff Model Implementation.

GR4J (Modèle du Génie Rural à 4 paramètres Journalier) is a 4-parameter
daily lumped rainfall-runoff model widely used in hydrology.

Parameters:
    X1: Production store capacity (mm)
    X2: Intercatchment exchange coefficient (mm/day)
    X3: Routing store capacity (mm)
    X4: Unit hydrograph time base (days)

Reference: Perrin, C., Michel, C., & Andréassian, V. (2003).
Improvement of a parsimonious model for streamflow simulation.
Journal of Hydrology, 279(1-4), 275-289.
"""
from __future__ import annotations

import math
from datetime import date as date_type, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

from backend.services.rainfall_service import read_dataset


# Default GR4J parameters (typical values for Indian basins)
DEFAULT_GR4J_PARAMS = {
    "X1": 300.0,  # Production store capacity (mm)
    "X2": 1.0,    # Exchange coefficient (mm/day)
    "X3": 50.0,   # Routing store capacity (mm)
    "X4": 2.0,    # Unit hydrograph time base (days)
}


def gr4j_model(
    rainfall: np.ndarray,
    pet: np.ndarray,
    params: dict[str, float],
    s_init: float | None = None,
    r_init: float | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Run GR4J model for a time series.

    Args:
        rainfall: Daily rainfall (mm) - shape (n_days,)
        pet: Daily potential evapotranspiration (mm) - shape (n_days,)
        params: GR4J parameters dict with X1, X2, X3, X4
        s_init: Initial production store level (mm)
        r_init: Initial routing store level (mm)

    Returns:
        Tuple of (discharge, production_store, routing_store) each shape (n_days,)
    """
    X1 = params["X1"]
    X2 = params["X2"]
    X3 = params["X3"]
    X4 = params["X4"]

    n = len(rainfall)
    if len(pet) != n:
        raise ValueError("Rainfall and PET must have same length")

    # Initialize stores
    s = s_init if s_init is not None else 0.6 * X1  # 60% of capacity
    r = r_init if r_init is not None else 0.7 * X3  # 70% of capacity

    # Unit hydrograph ordinates (SH1 for X4)
    uh_ordinates = _unit_hydrograph_ordinates(X4)
    uh_length = len(uh_ordinates)

    # Output arrays
    discharge = np.zeros(n)
    s_series = np.zeros(n)
    r_series = np.zeros(n)

    # Convolution buffer for unit hydrograph
    uh_buffer = np.zeros(uh_length + n)

    for t in range(n):
        P = max(0.0, rainfall[t])
        E = max(0.0, pet[t])

        # --- Production Store ---
        if P >= E:
            Pn = P - E
            # Production store filling (standard GR4J with tanh)
            ws = s / X1
            tanh_term = np.tanh(Pn / X1)
            Ps = X1 * (1 - ws**2) * tanh_term / (1 + ws * tanh_term)
            s = s + Ps
            # Percolation
            Perc = s * (1 - (1 + (4 * s / (9 * X1))**4)**(-0.25))
            s = s - Perc
            Pr = Pn - Ps + Perc
        else:
            En = E - P
            # Production store emptying (standard GR4J with tanh)
            ws = s / X1
            tanh_term = np.tanh(En / X1)
            Es = s * (2 - ws) * tanh_term / (1 + (1 - ws) * tanh_term)
            s = s - Es
            Perc = 0.0
            Pr = 0.0

        s = max(0.0, min(s, X1))  # Bound store
        s_series[t] = s

        # --- Routing Store ---
        # Split Pr into two components (90% and 10%)
        Pr1 = 0.9 * Pr
        Pr2 = 0.1 * Pr

        # Intercatchment exchange (can be negative)
        F = X2 * (r / X3)**3.5

        # Routing store level
        r = max(0.0, r + Pr1 + F)
        Qr = r * (1 - (1 + (r / X3)**4)**(-0.25))
        r = r - Qr

        # Add Qr to unit hydrograph convolution
        for i, ord_val in enumerate(uh_ordinates):
            if t + i < n + uh_length:
                uh_buffer[t + i] += Qr * ord_val

        # Direct runoff from Pr2
        Qd = Pr2 * uh_buffer[t]
        uh_buffer[t] = 0.0  # Clear processed

        # Total discharge
        discharge[t] = max(0.0, Qr + Qd)
        r = max(0.0, min(r, X3))  # Bound store
        r_series[t] = r

    return discharge, s_series, r_series


def _unit_hydrograph_ordinates(X4: float) -> np.ndarray:
    """Compute unit hydrograph ordinates (SH1) for given X4.

    Uses the standard GR4J unit hydrograph formulation.
    """
    n_ord = int(math.ceil(2 * X4))
    ordinates = np.zeros(n_ord)

    for i in range(1, n_ord + 1):
        t = i - 0.5
        if t <= X4:
            ordinates[i - 1] = (t / X4)**2.5 / 2.5
        else:
            t_prime = t - X4
            ordinates[i - 1] = 1 - 0.5 * (2 - t_prime / X4)**2.5 / 2.5

    # Normalize to sum to 1
    ordinates = ordinates / np.sum(ordinates)
    return ordinates


def _estimate_pet_from_temp(temp_c: np.ndarray, lat: float) -> np.ndarray:
    """Estimate PET using Hargreaves equation (simplified).

    PET = 0.0023 * (T_mean + 17.8) * (T_max - T_min)^0.5 * Ra
    where Ra is extraterrestrial radiation (simplified here).
    """
    # Simplified: assume T_max - T_min ≈ 10°C, Ra ≈ 15 mm/day
    # This is a rough approximation; real implementation needs daily Tmax/Tmin
    t_mean = temp_c
    pet = 0.0023 * (t_mean + 17.8) * np.sqrt(10.0) * 15.0
    return np.maximum(pet, 0.0)


def _get_basin_rainfall_pet(
    basin_id: str,
    start_date: str,
    end_date: str,
    rainfall_source: str = "imd_rf25",
) -> tuple[np.ndarray, np.ndarray]:
    """Extract basin-averaged rainfall and estimate PET for date range."""
    # For now, use national average rainfall as proxy
    # In production, this would use basin polygon to extract grid cells
    with read_dataset() as ds:
        rainfall_var = ds["RAINFALL"]
        time_coord = "TIME" if "TIME" in ds.coords else "time"
        lat_coord = "LATITUDE" if "LATITUDE" in ds.coords else "latitude"
        lon_coord = "LONGITUDE" if "LONGITUDE" in ds.coords else "longitude"

        start = date_type.fromisoformat(start_date)
        end = date_type.fromisoformat(end_date)

        # Select time slice
        time_slice = slice(start_date, end_date)
        rainfall_data = rainfall_var.sel({time_coord: time_slice})

        # National spatial average (all valid grid cells)
        rainfall_daily = []
        for t in range(rainfall_data.sizes[time_coord]):
            daily = rainfall_data.isel({time_coord: t}).values
            valid = daily[np.isfinite(daily)]
            if len(valid) > 0:
                rainfall_daily.append(float(np.mean(valid)))
            else:
                rainfall_daily.append(0.0)

    rainfall_arr = np.array(rainfall_daily)

    # Estimate PET from temperature (using a constant approximation for now)
    # In production, this would use temperature data
    pet_arr = np.full_like(rainfall_arr, 4.0)  # ~4 mm/day average for India

    return rainfall_arr, pet_arr


def run_gr4j_simulation(
    basin_id: str,
    start_date: str,
    end_date: str,
    rainfall_source: str = "imd_rf25",
    parameters: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Run GR4J simulation for a basin and date range.

    Returns discharge time series in m³/s (converted from mm/day over basin area).
    """
    params = {**DEFAULT_GR4J_PARAMS, **(parameters or {})}

    # Get rainfall and PET
    rainfall, pet = _get_basin_rainfall_pet(basin_id, start_date, end_date, rainfall_source)

    # Run GR4J
    discharge_mm, s_store, r_store = gr4j_model(rainfall, pet, params)

    # Convert mm/day to m³/s (approximate)
    # 1 mm over 1 km² = 1000 m³/day = 0.01157 m³/s
    # For Mahanadi delta sub-basin (~15,000 km²): 1 mm = 173.6 m³/s
    # This is a rough conversion; real implementation needs actual basin area
    BASIN_AREA_KM2 = {
        "mahanadi_delta_sub_1": 15000,
        "mahanadi_delta_sub_2": 12000,
    }
    area_km2 = BASIN_AREA_KM2.get(basin_id, 15000)
    mm_to_m3s = area_km2 * 1000 / 86400  # mm/day * km² -> m³/s
    discharge_m3s = discharge_mm * mm_to_m3s

    # Build date array
    start = date_type.fromisoformat(start_date)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(len(discharge_m3s))]

    return {
        "dates": dates,
        "discharge_m3s": discharge_m3s.tolist(),
        "discharge_mm_day": discharge_mm.tolist(),
        "production_store_mm": s_store.tolist(),
        "routing_store_mm": r_store.tolist(),
        "rainfall_mm": rainfall.tolist(),
        "pet_mm": pet.tolist(),
        "parameters": params,
        "basin_area_km2": area_km2,
    }


if __name__ == "__main__":
    # Quick test
    rainfall = np.array([10, 20, 5, 0, 0, 15, 30, 25, 10, 5] * 3, dtype=float)
    pet = np.array([4.0, 4.5, 3.5, 4.0, 4.0, 3.5, 4.0, 4.5, 4.0, 3.5] * 3, dtype=float)
    discharge, s, r = gr4j_model(rainfall, pet, DEFAULT_GR4J_PARAMS)
    print(f"Mean discharge: {np.mean(discharge):.2f} mm/day")
    print(f"Peak discharge: {np.max(discharge):.2f} mm/day")