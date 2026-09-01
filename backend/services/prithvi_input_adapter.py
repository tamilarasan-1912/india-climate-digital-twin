"""Validate MERRA-2 atmospheric inputs before Prithvi-WxC inference.

This adapter deliberately does not manufacture missing variables. The project
must use the official Prithvi-WxC variable ordering, units and normalization
before inference.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import xarray as xr

MODEL_NAME = "Prithvi-WxC-1.0-2300M-rollout"
MODEL_PROVIDER = "IBM / NASA"
EXPECTED_VARIABLE_COUNT = 160
INPUT_INTERVAL_HOURS = 6
FORECAST_LEAD_HOURS = 6


@dataclass(frozen=True)
class PrithviInputContract:
    model_name: str
    variable_count: int
    input_interval_hours: int
    forecast_lead_hours: int
    source: str


def get_input_contract() -> PrithviInputContract:
    return PrithviInputContract(
        model_name=MODEL_NAME,
        variable_count=EXPECTED_VARIABLE_COUNT,
        input_interval_hours=INPUT_INTERVAL_HOURS,
        forecast_lead_hours=FORECAST_LEAD_HOURS,
        source="MERRA-2 atmospheric fields",
    )


def validate_variables(variables: Sequence[str]) -> dict:
    supplied = list(variables)
    return {
        "valid": len(supplied) == EXPECTED_VARIABLE_COUNT,
        "expected_variable_count": EXPECTED_VARIABLE_COUNT,
        "supplied_variable_count": len(supplied),
        "variables": supplied,
    }


def validate_merra2_file(path: str | Path) -> dict:
    """Validate structural readiness of a local MERRA-2 NetCDF file.

    This is intentionally a structural check. Exact official model variable
    ordering, units and normalization remain a model-specific preprocessing
    responsibility and are not inferred here.
    """
    file_path = Path(path)
    if not file_path.exists():
        return {"valid": False, "path": str(file_path), "reason": "MERRA-2 file not found"}

    with xr.open_dataset(file_path, decode_times=True) as ds:
        variables = list(ds.data_vars)
        time_name = next((n for n in ("time", "valid_time", "TIME") if n in ds.coords or n in ds.dims), None)
        lat_name = next((n for n in ("lat", "latitude", "LATITUDE") if n in ds.coords or n in ds.dims), None)
        lon_name = next((n for n in ("lon", "longitude", "LONGITUDE") if n in ds.coords or n in ds.dims), None)
        timestamps = int(ds.sizes.get(time_name, 0)) if time_name else 0

        variable_check = validate_variables(variables)
        return {
            "valid": bool(variable_check["valid"] and time_name and lat_name and lon_name and timestamps >= 2),
            "path": str(file_path),
            "variable_count": len(variables),
            "expected_variable_count": EXPECTED_VARIABLE_COUNT,
            "timestamp_count": timestamps,
            "coordinates": {"time": time_name, "latitude": lat_name, "longitude": lon_name},
            "has_required_coordinates": bool(time_name and lat_name and lon_name),
            "has_two_timestamps": timestamps >= 2,
            "synthetic_variables_created": False,
            "variable_validation": variable_check,
            "note": "Official Prithvi-WxC variable ordering, units and normalization must be applied before inference.",
        }


def validate_current_imd_dataset() -> dict:
    supplied_variables = ("RAINFALL",)
    validation = validate_variables(supplied_variables)
    return {
        "dataset": "RF25_ind2024_rfp25.nc",
        "provider": "IMD",
        "variables": supplied_variables,
        "prithvi_compatible": False,
        "reason": "The current IMD dataset contains rainfall only; it is not the 160-variable MERRA-2-compatible input required by Prithvi-WxC.",
        "validation": validation,
    }


def print_configuration() -> None:
    contract = get_input_contract()
    print("=" * 70)
    print("INDIA CLIMATE DIGITAL TWIN")
    print("PRITHVI-WxC INPUT CONTRACT")
    print("=" * 70)
    print(f"Model: {contract.model_name}")
    print(f"Provider: {MODEL_PROVIDER}")
    print(f"Expected variables: {contract.variable_count}")
    print(f"Input interval: {contract.input_interval_hours} hours")
    print(f"Forecast lead: {contract.forecast_lead_hours} hours")
    print("-" * 70)
    result = validate_current_imd_dataset()
    print(f"Current dataset: {result['dataset']}")
    print(f"Prithvi compatible: {result['prithvi_compatible']}")
    print(result["reason"])
    print("=" * 70)


if __name__ == "__main__":
    print_configuration()
