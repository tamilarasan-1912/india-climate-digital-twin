"""Prepare and validate a real MERRA-2 NetCDF input package for Prithvi-WxC.

This script never creates synthetic atmospheric variables. It discovers local
MERRA-2 NetCDF files, normalizes common coordinate names, crops to the Chennai
area when requested, selects two timestamps, checks that the requested number
of atmospheric fields is present, and writes a compact JSON manifest.

Usage:
    python scripts/prepare_merra2_prithvi_input.py
    python scripts/prepare_merra2_prithvi_input.py --input path/to/file.nc

A real Prithvi-WxC rollout requires the official model's exact variable
contract and normalization. This script therefore stops at a validated,
traceable NetCDF package; it does not invent missing variables or weights.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "backend" / "data" / "merra2"
OUTPUT_DIR = DEFAULT_DIR / "prepared"

# Chennai bounding box used elsewhere in this project.
CHENNAI_BBOX = {"min_lon": 80.15, "min_lat": 12.90, "max_lon": 80.35, "max_lat": 13.20}
REQUIRED_VARIABLES = 160
REQUIRED_TIMESTAMPS = 2


def find_coord(ds: xr.Dataset, names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in ds.coords or name in ds.dims:
            return name
    return None


def discover(path: Path | None) -> list[Path]:
    if path:
        return [path]
    return sorted(DEFAULT_DIR.glob("*.nc"))


def prepare(path: Path) -> dict:
    with xr.open_dataset(path, decode_times=True) as ds:
        time_name = find_coord(ds, ("time", "valid_time", "TIME"))
        lat_name = find_coord(ds, ("lat", "latitude", "LATITUDE"))
        lon_name = find_coord(ds, ("lon", "longitude", "LONGITUDE"))
        variables = list(ds.data_vars)

        if not (time_name and lat_name and lon_name):
            raise ValueError("MERRA-2 file must contain time, latitude and longitude coordinates")

        if ds.sizes.get(time_name, 0) < REQUIRED_TIMESTAMPS:
            raise ValueError(f"At least {REQUIRED_TIMESTAMPS} timestamps are required")

        if len(variables) < REQUIRED_VARIABLES:
            raise ValueError(
                f"Found {len(variables)} data variables; Prithvi-WxC requires the official 160-variable input contract"
            )

        # Prefer a Chennai spatial subset when dimensions permit it. Do not
        # fail merely because a global grid uses descending latitude.
        subset = ds
        try:
            lat_values = np.asarray(ds[lat_name].values)
            lon_values = np.asarray(ds[lon_name].values)
            lat_slice = slice(CHENNAI_BBOX["max_lat"], CHENNAI_BBOX["min_lat"]) if lat_values[0] > lat_values[-1] else slice(CHENNAI_BBOX["min_lat"], CHENNAI_BBOX["max_lat"])
            lon_slice = slice(CHENNAI_BBOX["min_lon"], CHENNAI_BBOX["max_lon"])
            subset = ds.sel({lat_name: lat_slice, lon_name: lon_slice})
        except Exception:
            subset = ds

        if subset.sizes.get(lat_name, 0) == 0 or subset.sizes.get(lon_name, 0) == 0:
            raise ValueError("Chennai bounding box does not intersect the MERRA-2 grid")

        times = subset[time_name].values[:REQUIRED_TIMESTAMPS]
        selected = subset.isel({time_name: slice(0, REQUIRED_TIMESTAMPS)})

        # Force-read only the selected subset so NaN checks are real.
        nan_variables = []
        for name in variables:
            if time_name in selected[name].dims:
                values = selected[name].values
                if np.isnan(values).any():
                    nan_variables.append(name)

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output = OUTPUT_DIR / f"{path.stem}_chennai_pair.nc"
        selected.to_netcdf(output)

        manifest = {
            "source_file": str(path),
            "prepared_file": str(output),
            "variable_count": len(variables),
            "required_variable_count": REQUIRED_VARIABLES,
            "timestamp_count": REQUIRED_TIMESTAMPS,
            "timestamps": [str(t) for t in times],
            "coordinates": {"time": time_name, "latitude": lat_name, "longitude": lon_name},
            "spatial_subset": CHENNAI_BBOX,
            "shape": {k: int(v) for k, v in selected.sizes.items()},
            "variables_with_nan": nan_variables,
            "synthetic_variables_created": False,
            "ready_for_prithvi_contract": len(variables) == REQUIRED_VARIABLES and not nan_variables,
            "note": "Exact Prithvi-WxC variable ordering, units and normalization must be applied by the model adapter before inference.",
        }
        (OUTPUT_DIR / "merra2_prithvi_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="A local MERRA-2 NetCDF file")
    args = parser.parse_args()
    print("=" * 70)
    print("MERRA-2 → PRITHVI-WxC INPUT PREPARATION")
    print("=" * 70)
    files = discover(args.input)
    if not files:
        print(f"No MERRA-2 NetCDF files found in {DEFAULT_DIR}")
        print("Place an authenticated/downloaded MERRA-2 file there and rerun.")
        return
    for path in files:
        print(f"\nFILE: {path}")
        try:
            result = prepare(path)
            print(f"Variables             : {result['variable_count']}")
            print(f"Selected timestamps   : {result['timestamp_count']}")
            print(f"Prepared shape        : {result['shape']}")
            print(f"NaN-bearing variables : {len(result['variables_with_nan'])}")
            print(f"Ready for contract    : {result['ready_for_prithvi_contract']}")
            print(f"Prepared file         : {result['prepared_file']}")
        except Exception as exc:
            print(f"VALIDATION BLOCKED: {exc}")


if __name__ == "__main__":
    main()
