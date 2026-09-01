"""Prepare and validate a real MERRA-2 NetCDF input package for Prithvi-WxC.

No synthetic atmospheric variables are created. The script discovers local
MERRA-2 NetCDF files, validates coordinates and timestamps, crops to Chennai,
selects two timestamps, and writes a traceable prepared package plus manifest.
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
CHENNAI_BBOX = {"min_lon": 80.15, "min_lat": 12.90, "max_lon": 80.35, "max_lat": 13.20}
REQUIRED_VARIABLES = 160
REQUIRED_TIMESTAMPS = 2


def find_coord(ds: xr.Dataset, names: tuple[str, ...]) -> str | None:
    return next((name for name in names if name in ds.coords or name in ds.dims), None)


def discover(path: Path | None) -> list[Path]:
    return [path] if path else sorted(DEFAULT_DIR.glob("*.nc"))


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
        if len(variables) != REQUIRED_VARIABLES:
            raise ValueError(
                f"Found {len(variables)} data variables; expected the official {REQUIRED_VARIABLES}-variable Prithvi-WxC input contract"
            )

        lat_values = np.asarray(ds[lat_name].values)
        lat_slice = slice(CHENNAI_BBOX["max_lat"], CHENNAI_BBOX["min_lat"]) if lat_values[0] > lat_values[-1] else slice(CHENNAI_BBOX["min_lat"], CHENNAI_BBOX["max_lat"])
        lon_slice = slice(CHENNAI_BBOX["min_lon"], CHENNAI_BBOX["max_lon"])
        subset = ds.sel({lat_name: lat_slice, lon_name: lon_slice})
        if subset.sizes.get(lat_name, 0) == 0 or subset.sizes.get(lon_name, 0) == 0:
            raise ValueError("Chennai bounding box does not intersect the MERRA-2 grid")

        selected = subset.isel({time_name: slice(0, REQUIRED_TIMESTAMPS)})
        nan_variables = []
        for name in variables:
            if time_name in selected[name].dims and np.isnan(selected[name].values).any():
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
            "timestamps": [str(t) for t in selected[time_name].values],
            "coordinates": {"time": time_name, "latitude": lat_name, "longitude": lon_name},
            "spatial_subset": CHENNAI_BBOX,
            "shape": {k: int(v) for k, v in selected.sizes.items()},
            "variables_with_nan": nan_variables,
            "synthetic_variables_created": False,
            "ready_for_prithvi_contract": not nan_variables,
            "note": "Exact official Prithvi-WxC variable ordering, units and normalization must be applied before inference.",
        }
        (OUTPUT_DIR / "merra2_prithvi_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="A local MERRA-2 NetCDF file")
    args = parser.parse_args()
    files = discover(args.input)
    print("MERRA-2 → PRITHVI-WxC INPUT PREPARATION")
    if not files:
        print(f"No MERRA-2 NetCDF files found in {DEFAULT_DIR}")
        print("Place an authenticated/downloaded MERRA-2 file there and rerun.")
        return
    for path in files:
        try:
            result = prepare(path)
            print(f"FILE: {path}")
            print(f"Variables: {result['variable_count']}")
            print(f"Selected timestamps: {result['timestamp_count']}")
            print(f"Prepared shape: {result['shape']}")
            print(f"NaN-bearing variables: {len(result['variables_with_nan'])}")
            print(f"Ready for contract: {result['ready_for_prithvi_contract']}")
            print(f"Prepared file: {result['prepared_file']}")
        except Exception as exc:
            print(f"FILE: {path}")
            print(f"VALIDATION BLOCKED: {exc}")


if __name__ == "__main__":
    main()
