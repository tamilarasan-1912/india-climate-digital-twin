"""Build a real MERRA-2 -> Prithvi-WxC dynamic tensor.

This adapter never invents missing atmospheric data. It reads an existing
NetCDF dataset, validates the canonical Prithvi-WxC contract, and assembles
[batch, time, channel, lat, lon] in the official dynamic-channel ordering.
Normalization/scaling is intentionally a separate step because the official
Prithvi-WxC climatology files must be used rather than guessed statistics.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr

from backend.services.prithvi_input_adapter import (
    LEVELS,
    SURFACE_VARIABLES,
    VERTICAL_VARIABLES,
    validate_tensor_shape,
)

TIME_NAMES = ("time", "TIME")
LAT_NAMES = ("lat", "latitude", "LAT", "LATITUDE")
LON_NAMES = ("lon", "longitude", "LON", "LONGITUDE")
LEVEL_NAMES = ("lev", "level", "plev", "pressure", "LEVEL")


def _coord_name(ds: xr.Dataset, candidates: tuple[str, ...]) -> str:
    for name in candidates:
        if name in ds.coords or name in ds.dims:
            return name
    raise ValueError(f"Required coordinate not found; tried {candidates}")


def _normalise_level_values(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    # MERRA-2 model levels in the Prithvi contract are integer-like indices.
    return values


def _find_level_index(ds: xr.Dataset, variable: str) -> str:
    for name in LEVEL_NAMES:
        if name in ds[variable].dims:
            return name
    raise ValueError(f"Vertical variable {variable} has no pressure/model-level dimension")


def _select_level_indices(ds: xr.Dataset, variable: str, level_dim: str) -> list[int]:
    values = _normalise_level_values(ds[level_dim].values)
    indices: list[int] = []
    for target in LEVELS:
        matches = np.where(np.isclose(values, target, rtol=0, atol=1e-6))[0]
        if len(matches) != 1:
            raise ValueError(
                f"Dataset cannot provide Prithvi level {target:g} for {variable}; available levels={values.tolist()}"
            )
        indices.append(int(matches[0]))
    return indices


def _ensure_time_lat_lon(da: xr.DataArray, time_dim: str, lat_dim: str, lon_dim: str) -> xr.DataArray:
    missing = [x for x in (time_dim, lat_dim, lon_dim) if x not in da.dims]
    if missing:
        raise ValueError(f"Variable {da.name} is missing required dimensions: {missing}")
    return da.transpose(time_dim, lat_dim, lon_dim)


def _surface_array(ds: xr.Dataset, name: str, time_dim: str, lat_dim: str, lon_dim: str) -> np.ndarray:
    if name not in ds.data_vars:
        raise ValueError(f"Missing required surface variable: {name}")
    da = _ensure_time_lat_lon(ds[name], time_dim, lat_dim, lon_dim)
    return np.asarray(da.values, dtype=np.float32)


def _vertical_array(ds: xr.Dataset, name: str, time_dim: str, lat_dim: str, lon_dim: str) -> np.ndarray:
    if name not in ds.data_vars:
        raise ValueError(f"Missing required vertical variable: {name}")
    level_dim = _find_level_index(ds, name)
    indices = _select_level_indices(ds, name, level_dim)
    da = ds[name].isel({level_dim: indices})
    da = _ensure_time_lat_lon(da, time_dim, lat_dim, lon_dim)
    # [time, level, lat, lon]
    return np.asarray(da.values, dtype=np.float32)


def build_dynamic_tensor(path: str | Path) -> dict[str, Any]:
    """Assemble an unscaled dynamic tensor from a compatible NetCDF file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"MERRA-2 file does not exist: {path}")

    with xr.open_dataset(path) as ds:
        time_dim = _coord_name(ds, TIME_NAMES)
        lat_dim = _coord_name(ds, LAT_NAMES)
        lon_dim = _coord_name(ds, LON_NAMES)
        if ds.sizes[time_dim] != 2:
            raise ValueError(f"Prithvi-WxC rollout requires exactly 2 timestamps; got {ds.sizes[time_dim]}")

        times = ds[time_dim].values
        if len(times) != 2:
            raise ValueError("Exactly two timestamps are required")
        delta = (times[1] - times[0]) / np.timedelta64(1, "h")
        if not np.isclose(float(delta), 6.0):
            raise ValueError(f"Input timestamps must be 6 hours apart; got {delta:g} hours")

        channels: list[np.ndarray] = []
        channel_names: list[str] = []
        for name in SURFACE_VARIABLES:
            array = _surface_array(ds, name, time_dim, lat_dim, lon_dim)
            channels.append(array)
            channel_names.append(name)

        for name in VERTICAL_VARIABLES:
            array = _vertical_array(ds, name, time_dim, lat_dim, lon_dim)
            for level_index, level in enumerate(LEVELS):
                channels.append(array[:, level_index, :, :])
                channel_names.append(f"{name}@{level:g}")

        # stack -> [time, channel, lat, lon], then add batch dimension.
        dynamic = np.stack(channels, axis=1)
        tensor = dynamic[np.newaxis, ...]

        shape_result = validate_tensor_shape(tensor.shape)
        if not shape_result["valid"]:
            raise ValueError("Invalid assembled tensor: " + "; ".join(shape_result["errors"]))
        if not np.isfinite(tensor).all():
            raise ValueError("MERRA-2 tensor contains NaN or Inf values")

        return {
            "path": str(path),
            "tensor": tensor,
            "shape": list(tensor.shape),
            "channel_names": channel_names,
            "timestamps": [str(x) for x in times],
            "latitude_count": int(ds.sizes[lat_dim]),
            "longitude_count": int(ds.sizes[lon_dim]),
            "scaled": False,
            "normalization_required": True,
            "normalization_source": "official Prithvi-WxC MERRA-2 climatology",
        }


def inspect_input_file(path: str | Path) -> dict[str, Any]:
    """Return a safe manifest without loading the full tensor into the response."""
    result = build_dynamic_tensor(path)
    tensor = result.pop("tensor")
    result["tensor_bytes"] = int(tensor.nbytes)
    result["ready_for_scaling"] = True
    result["ready_for_model_forward"] = False
    result["blocker"] = "Official Prithvi-WxC input climatology/scaling and model runtime are still required."
    return result
