"""Official-style Prithvi-WxC preprocessing for MERRA-2 tensors.

Uses the model's published climatology files rather than estimating statistics
from the project dataset. This module intentionally fails closed when the
required climatology files are unavailable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import h5py
import numpy as np

from backend.services.merra2_tensor_service import build_dynamic_tensor
from backend.services.prithvi_input_adapter import LEVELS, SURFACE_VARIABLES, VERTICAL_VARIABLES

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLIMATOLOGY_DIR = PROJECT_ROOT / "models" / "prithvi-wxc" / "climatology"
SURFACE_CLIMATOLOGY = "musigma_surface.nc"
VERTICAL_CLIMATOLOGY = "musigma_vertical.nc"


def _read_scalers(path: Path, variables: tuple[str, ...], levels: tuple[float, ...] | None = None):
    if not path.exists():
        raise FileNotFoundError(f"Prithvi-WxC climatology file not found: {path}")
    with h5py.File(path, "r") as handle:
        stats = [x.decode().lower() if isinstance(x, bytes) else str(x).lower() for x in handle["statistic"][()]]
        mu_idx, sig_idx = stats.index("mu"), stats.index("sigma")
        if levels is None:
            mu = np.asarray([handle[name][()][mu_idx] for name in variables], dtype=np.float32)
            sig = np.asarray([handle[name][()][sig_idx] for name in variables], dtype=np.float32)
        else:
            available = np.asarray(handle["lev"][()])
            indices = []
            for level in levels:
                matches = np.where(np.isclose(available, level, rtol=0, atol=1e-6))[0]
                if len(matches) != 1:
                    raise ValueError(f"Climatology does not contain Prithvi pressure level {level:g}")
                indices.append(int(matches[0]))
            mu = np.concatenate([np.asarray(handle[name][()][mu_idx, indices], dtype=np.float32) for name in variables])
            sig = np.concatenate([np.asarray(handle[name][()][sig_idx, indices], dtype=np.float32) for name in variables])
    return mu, np.clip(sig, 1e-4, 1e4)


def scale_dynamic_tensor(tensor: np.ndarray, climatology_dir: str | Path = DEFAULT_CLIMATOLOGY_DIR) -> np.ndarray:
    """Scale [B,T,160,H,W] using official surface/vertical climatology."""
    climatology_dir = Path(climatology_dir)
    s_mu, s_sig = _read_scalers(climatology_dir / SURFACE_CLIMATOLOGY, SURFACE_VARIABLES)
    v_mu, v_sig = _read_scalers(climatology_dir / VERTICAL_CLIMATOLOGY, VERTICAL_VARIABLES, LEVELS)
    mu = np.concatenate([s_mu, v_mu]).reshape(1, 1, -1, 1, 1)
    sig = np.concatenate([s_sig, v_sig]).reshape(1, 1, -1, 1, 1)
    if tensor.shape[2] != mu.shape[2]:
        raise ValueError(f"Expected 160 channels, got {tensor.shape[2]}")
    return ((tensor.astype(np.float32) - mu) / sig).astype(np.float32)


def build_static_features(path: str | Path) -> np.ndarray:
    """Build the minimal time/location static features used by the official loader."""
    result = build_dynamic_tensor(path)
    tensor = result["tensor"]
    # Static spatial features: sin(lat), cos(lon), sin(lon), plus time-of-year
    # and hour encodings are generated from the first input timestamp.
    with h5py.File("/dev/null", "w") if False else __import__("contextlib").nullcontext():
        pass
    import xarray as xr
    with xr.open_dataset(path) as ds:
        lat_name = next(x for x in ("lat", "latitude", "LAT", "LATITUDE") if x in ds.coords or x in ds.dims)
        lon_name = next(x for x in ("lon", "longitude", "LON", "LONGITUDE") if x in ds.coords or x in ds.dims)
        lat = np.asarray(ds[lat_name].values, dtype=np.float32)
        lon = np.asarray(ds[lon_name].values, dtype=np.float32)
        time_name = next(x for x in ("time", "TIME") if x in ds.coords or x in ds.dims)
        timestamp = np.datetime64(ds[time_name].values[0], "h")
        day = int((timestamp.astype("datetime64[D]") - timestamp.astype("datetime64[Y]")).astype(int)) + 1
        hour = int((timestamp - timestamp.astype("datetime64[D]")).astype("timedelta64[h]").astype(int))
    lat_rad = np.deg2rad(lat)[:, None]
    lon_rad = np.deg2rad(lon)[None, :]
    spatial = np.stack([
        np.sin(lat_rad) * np.ones_like(lon_rad),
        np.ones_like(lat_rad) * np.cos(lon_rad),
        np.ones_like(lat_rad) * np.sin(lon_rad),
    ], axis=0).astype(np.float32)
    doy_angle = 2 * np.pi * day / 365.0
    hod_angle = 2 * np.pi * hour / 24.0
    time_features = np.stack([
        np.full_like(spatial[0], np.sin(doy_angle), dtype=np.float32),
        np.full_like(spatial[0], np.cos(doy_angle), dtype=np.float32),
        np.full_like(spatial[0], np.sin(hod_angle), dtype=np.float32),
        np.full_like(spatial[0], np.cos(hod_angle), dtype=np.float32),
    ], axis=0)
    return np.concatenate([spatial, time_features], axis=0)[None, ...]


def prepare_prithvi_input(path: str | Path, climatology_dir: str | Path = DEFAULT_CLIMATOLOGY_DIR) -> dict[str, Any]:
    raw = build_dynamic_tensor(path)
    scaled = scale_dynamic_tensor(raw["tensor"], climatology_dir)
    static = build_static_features(path)
    return {
        "path": raw["path"],
        "dynamic_shape": list(scaled.shape),
        "static_shape": list(static.shape),
        "dynamic": scaled,
        "static": static,
        "scaled": True,
        "scaling_source": "official Prithvi-WxC climatology",
        "channel_names": raw["channel_names"],
        "timestamps": raw["timestamps"],
    }


def inspect_preprocessing(path: str | Path, climatology_dir: str | Path = DEFAULT_CLIMATOLOGY_DIR) -> dict[str, Any]:
    prepared = prepare_prithvi_input(path, climatology_dir)
    return {k: v for k, v in prepared.items() if k not in {"dynamic", "static"}}
