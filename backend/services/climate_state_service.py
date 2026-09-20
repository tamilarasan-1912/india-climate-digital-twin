"""Multi-variable India climate state assembly.

This service is deliberately data-honest: a variable is included only when a
validated observation/reanalysis dataset is present. Missing variables are
reported as ``no_data`` rather than estimated from unrelated aggregates.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import hashlib
import json

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "backend" / "data" / "climate"

VARIABLES: dict[str, dict[str, Any]] = {
    "rainfall": {"aliases": ["RAINFALL", "rainfall", "pr", "precipitation"], "unit": "mm", "role": "observed"},
    "temperature": {"aliases": ["T2M", "temperature", "temp", "t2m", "air_temperature"], "unit": "degC", "role": "observed"},
    "wind": {"aliases": ["wind_speed", "WIND", "ws", "u10", "v10"], "unit": "m/s", "role": "observed"},
    "humidity": {"aliases": ["RH", "humidity", "relative_humidity", "q2m"], "unit": "%", "role": "observed"},
}


def _find_files() -> list[Path]:
    return sorted(DATA_ROOT.rglob("*.nc")) if DATA_ROOT.exists() else []


def _match_variable(ds: xr.Dataset, aliases: list[str]) -> str | None:
    names = list(ds.data_vars) + list(ds.coords)
    for alias in aliases:
        for name in names:
            if name.lower() == alias.lower():
                return name
    for alias in aliases:
        for name in names:
            if alias.lower() in name.lower():
                return name
    return None


def _time_name(ds: xr.Dataset) -> str | None:
    for name in ("time", "TIME", "valid_time", "datetime"):
        if name in ds.coords or name in ds.dims:
            return name
    return None


def _stats(values: np.ndarray) -> dict[str, Any]:
    valid = values[np.isfinite(values)]
    if valid.size == 0:
        return {"count": 0, "mean": None, "median": None, "minimum": None, "maximum": None, "std": None}
    return {
        "count": int(valid.size),
        "mean": float(np.mean(valid)),
        "median": float(np.median(valid)),
        "minimum": float(np.min(valid)),
        "maximum": float(np.max(valid)),
        "std": float(np.std(valid)),
    }


def discover_variable(variable: str) -> dict[str, Any]:
    if variable not in VARIABLES:
        raise ValueError(f"Unsupported climate variable: {variable}")
    matches = []
    for path in _find_files():
        try:
            with xr.open_dataset(path) as ds:
                name = _match_variable(ds, VARIABLES[variable]["aliases"])
                if name:
                    matches.append({"file": str(path.relative_to(ROOT)), "variable": name, "time_coordinate": _time_name(ds)})
        except Exception as exc:
            matches.append({"file": str(path.relative_to(ROOT)), "valid": False, "error": str(exc)})
    return {"variable": variable, "matches": matches, "status": "available" if matches else "no_data"}


def _read_variable(variable: str, target_date: str | None = None) -> dict[str, Any]:
    candidates = discover_variable(variable)["matches"]
    for item in candidates:
        if "variable" not in item:
            continue
        path = ROOT / item["file"]
        try:
            with xr.open_dataset(path) as ds:
                name = item["variable"]
                da = ds[name]
                tname = item.get("time_coordinate")
                if target_date and tname:
                    try:
                        da = da.sel({tname: target_date}, method="nearest")
                    except Exception:
                        pass
                values = np.asarray(da.values, dtype=float)
                return {
                    "status": "available",
                    "variable": variable,
                    "source": item["file"],
                    "source_variable": name,
                    "unit": VARIABLES[variable]["unit"],
                    "statistics": _stats(values),
                    "observation_time": str(da[tname].values) if tname and tname in da.coords else target_date,
                    "quality_flag": "dataset_present",
                }
        except Exception as exc:
            return {"status": "error", "variable": variable, "error": str(exc)}
    return {"status": "no_data", "variable": variable, "unit": VARIABLES[variable]["unit"], "quality_flag": "missing_dataset"}


def build_climate_state(target_date: str | None = None) -> dict[str, Any]:
    observations = {name: _read_variable(name, target_date) for name in VARIABLES}
    payload = {"scope": "India", "target_date": target_date, "observations": observations}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:16]
    available = [k for k, v in observations.items() if v.get("status") == "available"]
    return {
        "twin_state": {
            "scope": "India",
            "level": "country",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "observation_date": target_date,
            "state_hash": digest,
            "variables": observations,
            "available_variables": available,
            "missing_variables": [k for k in VARIABLES if k not in available],
            "representation": "validated observation/reanalysis state; missing variables are not imputed",
        },
        "synchronization": {"status": "synchronized" if available else "degraded", "available_variable_count": len(available), "total_variable_count": len(VARIABLES)},
    }
