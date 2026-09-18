"""Cloud-friendly climate raster contract and tile preparation utilities.

This module deliberately separates:
1. source NetCDF/Zarr data,
2. validated spatial subsets,
3. browser-facing tile metadata.

It does not invent data and does not require a tile server to be installed.
When rio-tiler/TiTiler or another OGC tile service is connected later, the
returned contract can point the frontend at it without changing layer semantics.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr


def raster_contract(
    *,
    layer: str,
    provider: str,
    variable: str,
    units: str,
    source_path: str | None,
    date: str,
    min_zoom: int = 3,
    max_zoom: int = 10,
) -> dict[str, Any]:
    return {
        "contract": "india-climate-raster/v1",
        "layer": layer,
        "provider": provider,
        "variable": variable,
        "units": units,
        "date": date,
        "format": "Cloud Optimized GeoTIFF / tiled coverage",
        "tiling": {
            "scheme": "WebMercatorQuad",
            "min_zoom": min_zoom,
            "max_zoom": max_zoom,
            "tile_size": 256,
            "endpoint_template": f"/api/climate/tiles/{layer}/{date}/{{z}}/{{x}}/{{y}}.png",
        },
        "source": source_path,
        "data_policy": "Tile metadata never implies that a source is connected; only validated provider adapters may expose values.",
    }


def validate_regular_grid(
    dataset: xr.Dataset,
    variable: str,
    *,
    latitude: str = "LATITUDE",
    longitude: str = "LONGITUDE",
) -> dict[str, Any]:
    if variable not in dataset:
        raise ValueError(f"Variable '{variable}' is not present in dataset")
    da = dataset[variable]
    if latitude not in dataset.coords and latitude not in dataset:
        raise ValueError(f"Latitude coordinate '{latitude}' is missing")
    if longitude not in dataset.coords and longitude not in dataset:
        raise ValueError(f"Longitude coordinate '{longitude}' is missing")
    lat = np.asarray(dataset[latitude].values, dtype=float)
    lon = np.asarray(dataset[longitude].values, dtype=float)
    if lat.ndim != 1 or lon.ndim != 1:
        raise ValueError("Only 1-D regular latitude/longitude grids are supported")
    if len(lat) < 2 or len(lon) < 2:
        raise ValueError("Grid must contain at least two latitude and longitude points")
    lat_step = float(np.median(np.diff(lat)))
    lon_step = float(np.median(np.diff(lon)))
    return {
        "variable": variable,
        "dimensions": {k: int(v) for k, v in da.sizes.items()},
        "latitude": {"min": float(np.min(lat)), "max": float(np.max(lat)), "step": abs(lat_step)},
        "longitude": {"min": float(np.min(lon)), "max": float(np.max(lon)), "step": abs(lon_step)},
        "units": da.attrs.get("units"),
    }


def spatial_subset(
    dataset: xr.Dataset,
    variable: str,
    bbox: tuple[float, float, float, float],
    *,
    latitude: str = "LATITUDE",
    longitude: str = "LONGITUDE",
) -> xr.DataArray:
    min_lon, min_lat, max_lon, max_lat = bbox
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("Invalid bounding box")
    if latitude not in dataset or longitude not in dataset:
        raise ValueError("Dataset has no required spatial coordinates")
    da = dataset[variable]
    lat_values = np.asarray(dataset[latitude].values)
    lat_slice = slice(min_lat, max_lat) if lat_values[0] < lat_values[-1] else slice(max_lat, min_lat)
    return da.sel({latitude: lat_slice, longitude: slice(min_lon, max_lon)})


def grid_stats(data: xr.DataArray) -> dict[str, Any]:
    values = np.asarray(data.values, dtype=np.float64)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"valid": 0, "min": None, "max": None, "mean": None}
    return {
        "valid": int(finite.size),
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
    }


def tile_xyz_bounds(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    if z < 0 or x < 0 or y < 0 or x >= 2**z or y >= 2**z:
        raise ValueError("Invalid XYZ tile coordinates")
    n = 2**z
    west = x / n * 360.0 - 180.0
    east = (x + 1) / n * 360.0 - 180.0
    north = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    south = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1) / n))))
    return west, south, east, north


def discover_netcdf(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Climate dataset not found: {p}")
    with xr.open_dataset(p) as ds:
        return {
            "path": str(p),
            "variables": sorted(ds.data_vars),
            "coordinates": sorted(ds.coords),
            "sizes": {k: int(v) for k, v in ds.sizes.items()},
        }
