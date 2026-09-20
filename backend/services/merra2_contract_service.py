"""Structural MERRA-2 contract inspection for Prithvi-WxC.

This service deliberately does not invent missing atmospheric variables,
normalization statistics, or forecast values. It inventories local NetCDF
assets and reports whether their structure is sufficient for the next stage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MERRA2_DIRECTORY = PROJECT_ROOT / "backend" / "data" / "merra2"
REQUIRED_VARIABLE_COUNT = 160
REQUIRED_TIMESTEPS = 2
REQUIRED_INTERVAL_HOURS = 6


def discover_merra2_files() -> list[Path]:
    if not MERRA2_DIRECTORY.exists():
        return []
    return sorted(MERRA2_DIRECTORY.glob("*.nc"))


def _coord_name(ds: xr.Dataset, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in ds.coords or name in ds.dims:
            return name
    return None


def _time_metadata(ds: xr.Dataset) -> dict[str, Any]:
    name = _coord_name(ds, ("time", "TIME"))
    if not name:
        return {"name": None, "count": 0, "interval_hours": None}
    values = np.asarray(ds[name].values)
    count = int(values.size)
    interval_hours = None
    if count >= 2:
        try:
            delta = values[1] - values[0]
            interval_hours = float(delta / np.timedelta64(1, "h"))
        except (TypeError, ValueError, OverflowError):
            interval_hours = None
    return {"name": name, "count": count, "interval_hours": interval_hours}


def inspect_merra2_file(path: Path) -> dict[str, Any]:
    with xr.open_dataset(path) as ds:
        time = _time_metadata(ds)
        lat = _coord_name(ds, ("lat", "latitude", "LATITUDE"))
        lon = _coord_name(ds, ("lon", "longitude", "LONGITUDE"))
        variables = sorted(str(v) for v in ds.data_vars)
        dimensions = {str(k): int(v) for k, v in ds.sizes.items()}
        return {
            "file": str(path),
            "variables": variables,
            "variable_count": len(variables),
            "dimensions": dimensions,
            "time": time,
            "latitude": {"name": lat, "size": dimensions.get(lat) if lat else None},
            "longitude": {"name": lon, "size": dimensions.get(lon) if lon else None},
            "units": {v: str(ds[v].attrs.get("units", "")) for v in variables},
        }


def build_contract_report() -> dict[str, Any]:
    files = discover_merra2_files()
    inventories: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for path in files:
        try:
            inventories.append(inspect_merra2_file(path))
        except Exception as exc:
            errors.append({"file": str(path), "error": str(exc)})

    variable_sets = [set(item["variables"]) for item in inventories]
    union = sorted(set().union(*variable_sets)) if variable_sets else []
    intersection = sorted(set.intersection(*variable_sets)) if variable_sets else []
    time_counts = [int(item["time"]["count"]) for item in inventories]
    intervals = [item["time"]["interval_hours"] for item in inventories if item["time"]["interval_hours"] is not None]
    cadence_ok = bool(intervals) and all(abs(x - REQUIRED_INTERVAL_HOURS) < 1e-6 for x in intervals)
    timestep_ok = bool(time_counts) and max(time_counts) >= REQUIRED_TIMESTEPS
    variable_count_ok = len(intersection) >= REQUIRED_VARIABLE_COUNT
    structural_ok = bool(inventories) and not errors and all(
        item["time"]["name"] and item["latitude"]["name"] and item["longitude"]["name"]
        for item in inventories
    )
    ready = structural_ok and variable_count_ok and timestep_ok and cadence_ok
    return {
        "status": "ready" if ready else "blocked",
        "directory": str(MERRA2_DIRECTORY),
        "file_count": len(files),
        "valid_file_count": len(inventories),
        "errors": errors,
        "contract": {
            "required_variable_count": REQUIRED_VARIABLE_COUNT,
            "validated_common_variable_count": len(intersection),
            "validated_union_variable_count": len(union),
            "required_timesteps": REQUIRED_TIMESTEPS,
            "required_interval_hours": REQUIRED_INTERVAL_HOURS,
            "synthetic_values_allowed": False,
            "normalization_source": "official Prithvi-WxC rollout configuration/assets; not inferred here",
        },
        "checks": {
            "files_present": bool(files),
            "basic_structure": structural_ok,
            "common_variable_count": variable_count_ok,
            "two_or_more_timesteps": timestep_ok,
            "six_hour_cadence": cadence_ok,
        },
        "variables": {
            "common": intersection,
            "union": union,
        },
        "inventories": inventories,
        "next_step": "Provide validated official MERRA-2/Prithvi-WxC contract assets before model inference." if not ready else "Proceed to official tensor ordering, normalization, static fields, and model-runtime validation.",
    }
