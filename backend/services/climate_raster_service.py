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

def render_rainfall_xyz_tile(
    dataset_path: str | Path,
    date: str,
    z: int,
    x: int,
    y: int,
    size: int = 256,
) -> bytes:
    """Render a validated rainfall grid into a transparent PNG XYZ tile.

    This is a provider-backed renderer: if the source NetCDF is absent or the
    requested date is absent, it raises instead of creating synthetic values.
    """
    from io import BytesIO
    from PIL import Image

    if size not in (256, 512):
        raise ValueError("Tile size must be 256 or 512")
    west, south, east, north = tile_xyz_bounds(z, x, y)
    if west >= 180.0:
        # Tile lies entirely east of the antimeridian: no data, empty tile.
        return _transparent_png(size)
    east = min(east, 179.999)
    with xr.open_dataset(dataset_path) as ds:
        variable = "RAINFALL"
        if variable not in ds:
            raise ValueError("Rainfall variable RAINFALL is missing")
        try:
            da = ds[variable].sel(TIME=date)
        except Exception as exc:
            raise ValueError(f"Rainfall date '{date}' is unavailable") from exc
        lat_name, lon_name = "LATITUDE", "LONGITUDE"
        lat = np.asarray(ds[lat_name].values, dtype=float)
        lon = np.asarray(ds[lon_name].values, dtype=float)
        values = np.asarray(da.values, dtype=float)
        if values.ndim != 2:
            raise ValueError("Rainfall tile renderer requires a 2-D daily grid")
        if lat[0] > lat[-1]:
            lat = lat[::-1]
            values = values[::-1, :]
        # Web-map pixel centers.
        px = np.linspace(west, east, size, endpoint=False) + (east - west) / (2 * size)
        py = np.linspace(north, south, size, endpoint=False) - (north - south) / (2 * size)
        lon_idx = np.searchsorted(lon, px).clip(1, len(lon) - 1)
        lon_idx = np.where(np.abs(lon[lon_idx] - px) < np.abs(lon[lon_idx - 1] - px), lon_idx, lon_idx - 1)
        lat_idx = np.searchsorted(lat, py).clip(1, len(lat) - 1)
        lat_idx = np.where(np.abs(lat[lat_idx] - py) < np.abs(lat[lat_idx - 1] - py), lat_idx, lat_idx - 1)
        grid = values[np.ix_(lat_idx, lon_idx)]
        valid = np.isfinite(grid) & (grid >= 0) & (grid <= 10000)
        rgba = np.zeros((size, size, 4), dtype=np.uint8)
        if np.any(valid):
            # Stable visualization ramp; values remain provider-derived.
            # Compute in float, clip, then cast so NaN/overflow warnings cannot
            # corrupt the ramp.
            t = np.clip(grid / 100.0, 0.0, 1.0)
            red = np.where(valid, np.clip(255.0 * t, 0, 255), 0).astype(np.uint8)
            green = np.where(valid, np.clip(220.0 * (1.0 - t), 0, 255), 0).astype(np.uint8)
            blue = np.where(valid, np.clip(255.0 - red.astype(np.float64) / 2.0, 0, 255), 0).astype(np.uint8)
            rgba[..., 0] = red
            rgba[..., 1] = green
            rgba[..., 2] = blue
            rgba[..., 3] = np.where(valid, 210, 0).astype(np.uint8)
        image = Image.fromarray(rgba, mode="RGBA")
        buf = BytesIO()
        image.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


def _transparent_png(size: int) -> bytes:
    from io import BytesIO
    from PIL import Image

    buf = BytesIO()
    Image.new("RGBA", (size, size), (0, 0, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()
