"""
India Climate Digital Twin
Step 11D.2 - MERRA-2 Input Validator

Validates a local MERRA-2 NetCDF file before it is supplied
to Prithvi-WxC.

This module does NOT download model weights and does NOT
generate synthetic atmospheric variables.
"""

from __future__ import annotations

from pathlib import Path

import xarray as xr


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MERRA2_DIRECTORY = (
    PROJECT_ROOT
    / "backend"
    / "data"
    / "merra2"
)


# ============================================================
# DISCOVER FILES
# ============================================================

def discover_files() -> list[Path]:

    if not MERRA2_DIRECTORY.exists():

        return []

    return sorted(
        MERRA2_DIRECTORY.glob("*.nc")
    )


# ============================================================
# INSPECT DATASET
# ============================================================

def inspect_dataset(
    path: Path,
) -> dict:

    with xr.open_dataset(path) as ds:

        return {

            "file":
                str(path),

            "dimensions":
                {
                    key: int(value)
                    for key, value
                    in ds.sizes.items()
                },

            "coordinates":
                list(ds.coords),

            "variables":
                list(ds.data_vars),

            "attributes":
                dict(ds.attrs),

        }


# ============================================================
# VALIDATION
# ============================================================

def validate_dataset(
    path: Path,
) -> dict:

    information = inspect_dataset(
        path
    )

    dimensions = (
        information["dimensions"]
    )

    variables = (
        information["variables"]
    )

    has_time = (
        "time" in dimensions
        or "TIME" in dimensions
    )

    has_latitude = (
        "lat" in dimensions
        or "latitude" in dimensions
        or "LATITUDE" in dimensions
    )

    has_longitude = (
        "lon" in dimensions
        or "longitude" in dimensions
        or "LONGITUDE" in dimensions
    )

    return {

        "file":
            information["file"],

        "variable_count":
            len(variables),

        "variables":
            variables,

        "has_time":
            has_time,

        "has_latitude":
            has_latitude,

        "has_longitude":
            has_longitude,

        "basic_structure_valid":
            (
                has_time
                and has_latitude
                and has_longitude
            ),

    }


# ============================================================
# CLI
# ============================================================

def run() -> None:

    print("=" * 70)
    print("INDIA CLIMATE DIGITAL TWIN")
    print("MERRA-2 INPUT VALIDATION")
    print("=" * 70)

    print()

    print(
        f"Expected directory:\n"
        f"{MERRA2_DIRECTORY}"
    )

    files = discover_files()

    print()

    if not files:

        print(
            "No MERRA-2 NetCDF files found."
        )

        print()

        print(
            "This is expected at this stage."
        )

        print(
            "The validator is ready for "
            "a compatible sample dataset."
        )

        print()

        print("=" * 70)

        return

    print(
        f"Found {len(files)} NetCDF file(s)."
    )

    for path in files:

        print()
        print("-" * 70)
        print(
            f"FILE: {path.name}"
        )
        print("-" * 70)

        result = validate_dataset(
            path
        )

        print(
            f"Variables: "
            f"{result['variable_count']}"
        )

        print(
            f"Time dimension: "
            f"{result['has_time']}"
        )

        print(
            f"Latitude dimension: "
            f"{result['has_latitude']}"
        )

        print(
            f"Longitude dimension: "
            f"{result['has_longitude']}"
        )

        print(
            f"Basic structure valid: "
            f"{result['basic_structure_valid']}"
        )

        print()

        print("Variables:")

        for variable in result[
            "variables"
        ]:

            print(
                f"  - {variable}"
            )

    print()
    print("=" * 70)


if __name__ == "__main__":
    run()
