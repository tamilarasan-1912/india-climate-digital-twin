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


def _estimate_pet_from_temp(temp_c: np.ndarray) -> np.ndarray:
    """Legacy PET estimation from temperature array."""
    t_mean = temp_c
    pet = 0.0023 * (t_mean + 17.8) * np.sqrt(10.0) * 15.0
    return np.maximum(pet, 0.0)


# Basin configurations with metadata from pilot data
BASIN_CONFIGS = {
    "mahanadi_delta_sub_1": {
        "area_km2": 15000,
        "bbox": {"min_lon": 80.5, "max_lon": 87.5, "min_lat": 18.5, "max_lat": 23.5},
        "dem_path": "/workspace/f3031bab-c4f7-4425-9cd8-fb4088af3cb6/sessions/backend/data/basins/mahanadi_delta/dem_copernicus_30m.nc",
        "landcover_path": "/workspace/f3031bab-c4f7-4425-9cd8-fb4088af3cb6/sessions/backend/data/basins/mahanadi_delta/worldcover_10m.nc",
        "metadata_path": "/workspace/f3031bab-c4f7-4425-9cd8-fb4088af3cb6/sessions/backend/data/basins/mahanadi_delta/basin_metadata.json",
    },
    "mahanadi_delta_sub_2": {
        "area_km2": 12000,
        "bbox": {"min_lon": 83.0, "max_lon": 86.5, "min_lat": 19.5, "max_lat": 22.0},
        "dem_path": "/workspace/f3031bab-c4f7-4425-9cd8-fb4088af3cb6/sessions/backend/data/basins/mahanadi_delta/dem_copernicus_30m.nc",
        "landcover_path": "/workspace/f3031bab-c4f7-4425-9cd8-fb4088af3cb6/sessions/backend/data/basins/mahanadi_delta/worldcover_10m.nc",
        "metadata_path": "/workspace/f3031bab-c4f7-4425-9cd8-fb4088af3cb6/sessions/backend/data/basins/mahanadi_delta/basin_metadata.json",
    },
}


def _load_basin_config(basin_id: str) -> dict[str, Any]:
    """Load basin configuration and metadata."""
    config = BASIN_CONFIGS.get(basin_id, BASIN_CONFIGS["mahanadi_delta_sub_1"]).copy()
    
    # Try to load metadata for additional info
    meta_path = Path(config["metadata_path"])
    if meta_path.exists():
        try:
            with open(meta_path) as f:
                metadata = json.load(f)
            config["metadata"] = metadata
        except Exception:
            pass
    
    return config


def _load_dem(basin_id: str) -> xr.DataArray | None:
    """Load DEM for basin."""
    config = _load_basin_config(basin_id)
    dem_path = Path(config["dem_path"])
    if not dem_path.exists():
        return None
    try:
        return xr.open_dataarray(dem_path)
    except Exception:
        return None


def _load_landcover(basin_id: str) -> xr.DataArray | None:
    """Load land cover for basin."""
    config = _load_basin_config(basin_id)
    lc_path = Path(config["landcover_path"])
    if not lc_path.exists():
        return None
    try:
        return xr.open_dataarray(lc_path)
    except Exception:
        return None


def _estimate_pet_from_elevation(
    elevation: np.ndarray,
    lat: np.ndarray,
    day_of_year: int,
) -> float:
    """Estimate PET using Hargreaves-Samani equation with elevation correction.
    
    PET = 0.0023 * (T_mean + 17.8) * sqrt(T_max - T_min) * Ra
    
    With elevation correction: T decreases ~6.5°C per 1000m
    """
    # Mean elevation of basin (m)
    mean_elev = float(np.nanmean(elevation))
    
    # Approximate temperature at sea level for this latitude/day
    # Simplified: T_mean ≈ 25 - 0.01 * lat - 0.0065 * elev
    mean_lat = float(np.nanmean(lat))
    t_mean = 25.0 - 0.01 * mean_lat - 0.0065 * mean_elev
    t_range = 10.0  # Assumed diurnal range
    
    # Extraterrestrial radiation (simplified)
    # Ra ≈ 15 MJ/m²/day for India latitudes
    ra = 15.0
    
    pet = 0.0023 * (t_mean + 17.8) * math.sqrt(t_range) * ra
    return max(0.0, pet)


def _get_basin_rainfall_pet(
    basin_id: str,
    start_date: str,
    end_date: str,
    rainfall_source: str = "imd_rf25",
) -> tuple[np.ndarray, np.ndarray]:
    """Extract basin-averaged rainfall and estimate PET for date range.
    
    Uses basin bbox to clip IMD rainfall grid, and DEM for PET estimation.
    """
    config = _load_basin_config(basin_id)
    bbox = config["bbox"]
    
    with read_dataset() as ds:
        rainfall_var = ds["RAINFALL"]
        time_coord = "TIME" if "TIME" in ds.coords else "time"
        lat_coord = "LATITUDE" if "LATITUDE" in ds.coords else "latitude"
        lon_coord = "LONGITUDE" if "LONGITUDE" in ds.coords else "longitude"
        
        lats = ds[lat_coord].values
        lons = ds[lon_coord].values
        
        # Find grid cells within basin bbox
        lat_mask = (lats >= bbox["min_lat"]) & (lats <= bbox["max_lat"])
        lon_mask = (lons >= bbox["min_lon"]) & (lons <= bbox["max_lon"])
        
        # Select time slice
        time_slice = slice(start_date, end_date)
        rainfall_data = rainfall_var.sel({time_coord: time_slice})
        
        # Basin spatial average (only grid cells within bbox)
        rainfall_daily = []
        for t in range(rainfall_data.sizes[time_coord]):
            daily = rainfall_data.isel({time_coord: t}).values
            # Mask to basin bbox
            basin_daily = daily[lat_mask, :][:, lon_mask]
            valid = basin_daily[np.isfinite(basin_daily)]
            if len(valid) > 0:
                rainfall_daily.append(float(np.mean(valid)))
            else:
                rainfall_daily.append(0.0)

    rainfall_arr = np.array(rainfall_daily)
    
    # Estimate PET using basin DEM
    dem = _load_dem(basin_id)
    if dem is not None:
        # Get mean elevation and latitude for basin
        elev_values = dem.values
        # Coordinates are in the dataarray
        dem_lats = dem.coords["lat"].values if "lat" in dem.coords else np.array([21.0])
        
        # Estimate PET for each day (simplified - same PET for all days)
        pet_daily = []
        start_dt = date_type.fromisoformat(start_date)
        for i, _ in enumerate(rainfall_daily):
            doy = (start_dt + timedelta(days=i)).timetuple().tm_yday
            pet = _estimate_pet_from_elevation(elev_values, dem_lats, doy)
            pet_daily.append(pet)
        pet_arr = np.array(pet_daily)
    else:
        # Fallback: constant PET
        pet_arr = np.full_like(rainfall_arr, 4.0)  # ~4 mm/day average for India
    
    return rainfall_arr, pet_arr


def _estimate_gr4j_params_from_basin(basin_id: str) -> dict[str, float]:
    """Estimate initial GR4J parameters from basin characteristics.
    
    Uses area, elevation, land cover to provide better initial guess.
    """
    config = _load_basin_config(basin_id)
    area_km2 = config["area_km2"]
    
    # Load DEM for elevation statistics
    dem = _load_dem(basin_id)
    mean_elev = 100.0
    if dem is not None:
        mean_elev = float(np.nanmean(dem.values))
    
    # Load land cover for soil/vegetation info
    lc = _load_landcover(basin_id)
    forest_frac = 0.3
    if lc is not None:
        # Class 10 = Tree cover
        forest_frac = float(np.sum(lc.values == 10) / lc.size)
    
    # Empirical relationships for Indian basins (approximate)
    # X1: Production store capacity - related to soil depth, vegetation
    # X2: Exchange coefficient - related to geology, aquifer
    # X3: Routing store capacity - related to basin size, channel network
    # X4: Unit hydrograph time base - related to basin length, slope
    
    # Scale X1 with forest cover (more forest -> higher storage)
    X1 = 200 + 200 * forest_frac  # 200-400 mm
    
    # X2: Small for Indian basins (typically 0.1-2.0)
    X2 = 0.5
    
    # X3 scales with basin area (roughly)
    X3 = 20 + 0.002 * area_km2  # 20-50 mm
    
    # X4 relates to basin length / slope (from DEM)
    X4 = 1.5 + 0.0005 * mean_elev  # 1.5-3 days
    
    return {
        "X1": X1,
        "X2": X2,
        "X3": X3,
        "X4": X4,
    }


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
    config = _load_basin_config(basin_id)
    area_km2 = config["area_km2"]
    
    # Use estimated parameters if none provided
    if parameters is None:
        parameters = _estimate_gr4j_params_from_basin(basin_id)
    params = {**DEFAULT_GR4J_PARAMS, **parameters}

    # Get rainfall and PET
    rainfall, pet = _get_basin_rainfall_pet(basin_id, start_date, end_date, rainfall_source)

    # Run GR4J
    discharge_mm, s_store, r_store = gr4j_model(rainfall, pet, params)

    # Convert mm/day to m³/s (approximate)
    # 1 mm over 1 km² = 1000 m³/day = 0.01157 m³/s
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