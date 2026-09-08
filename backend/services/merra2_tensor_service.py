"""Validated MERRA-2 -> Prithvi-WxC tensor preparation boundary.

This module prepares a structural tensor contract only when the source data
actually contains the required fields. It deliberately does not invent,
interpolate, normalize, reorder, or rename atmospheric variables without an
explicit model manifest.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

from backend.services.merra2_input_validator import discover_files
from backend.services.prithvi_input_adapter import EXPECTED_VARIABLE_COUNT, INPUT_INTERVAL_HOURS


def _coord(ds: xr.Dataset, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in ds.coords or name in ds.dims:
            return name
    return None


def inspect_tensor_inputs(paths: list[Path] | None = None) -> dict[str, Any]:
    files = paths if paths is not None else discover_files()
    reports: list[dict[str, Any]] = []
    union: set[str] = set()
    intersection: set[str] | None = None
    for path in files:
        with xr.open_dataset(path) as ds:
            variables = set(ds.data_vars)
            union |= variables
            intersection = variables.copy() if intersection is None else intersection & variables
            time_name = _coord(ds, ("time", "TIME", "Time"))
            lat_name = _coord(ds, ("lat", "latitude", "LATITUDE"))
            lon_name = _coord(ds, ("lon", "longitude", "LONGITUDE"))
            times = []
            if time_name:
                times = [str(value) for value in ds[time_name].values]
            reports.append({
                "file": str(path),
                "variables": sorted(variables),
                "variable_count": len(variables),
                "time_coordinate": time_name,
                "latitude_coordinate": lat_name,
                "longitude_coordinate": lon_name,
                "time_values": times,
                "dimensions": {key: int(value) for key, value in ds.sizes.items()},
            })

    return {
        "files_found": len(files),
        "files": reports,
        "union_variable_count": len(union),
        "intersection_variable_count": len(intersection or set()),
        "union_variables": sorted(union),
        "intersection_variables": sorted(intersection or set()),
        "required_variable_count": EXPECTED_VARIABLE_COUNT,
        "input_interval_hours": INPUT_INTERVAL_HOURS,
    }


def build_tensor_contract(paths: list[Path] | None = None) -> dict[str, Any]:
    inventory = inspect_tensor_inputs(paths)
    reasons: list[str] = []
    selected: list[dict[str, Any]] = []

    for report in inventory["files"]:
        times = report["time_values"]
        cadence_ok = False
        if len(times) >= 2:
            try:
                parsed = np.array(times, dtype="datetime64[ns]")
                deltas = np.diff(parsed).astype("timedelta64[h]").astype(int)
                cadence_ok = bool(np.all(deltas == INPUT_INTERVAL_HOURS))
            except (TypeError, ValueError):
                cadence_ok = False
        if report["variable_count"] >= EXPECTED_VARIABLE_COUNT and cadence_ok and len(times) >= 2:
            selected.append(report)

    if not selected:
        reasons.append("No local MERRA-2 file currently satisfies the structural two-timestamp, 6-hour, 160-variable gate.")

    return {
        "status": "ready" if selected else "blocked",
        "model": "ibm-nasa-geospatial/Prithvi-WxC-1.0-2300M-rollout",
        "required": {
            "timestamps": 2,
            "variables": EXPECTED_VARIABLE_COUNT,
            "interval_hours": INPUT_INTERVAL_HOURS,
        },
        "selected_inputs": selected,
        "inventory": inventory,
        "reasons": reasons,
        "tensor_built": False,
        "normalization": "not_applied_without_official_model_statistics",
        "variable_order": "not_applied_without_official_model_manifest",
        "synthetic_values_used": False,
    }
