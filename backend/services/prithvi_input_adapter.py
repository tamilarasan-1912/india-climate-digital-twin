"""
India Climate Digital Twin
Step 11D.2 - Prithvi WxC MERRA-2 Input Contract

Purpose:
    Validate the semantic MERRA-2 input contract required by the official
    Prithvi WxC rollout model before any inference is attempted.

Scientific guardrail:
    The current project IMD rainfall dataset is not a Prithvi WxC input.
    This module never fabricates missing atmospheric variables.

Official Prithvi WxC dynamic input contract:
    20 surface variables + (10 vertical variables x 14 pressure levels)
    = 160 dynamic channels.

The canonical variable names, units and levels below are aligned with the
NASA-IMPACT Prithvi-WxC definitions.py contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Mapping, Sequence


MODEL_NAME = "Prithvi-WxC-1.0-2300M-rollout"
MODEL_PROVIDER = "IBM / NASA"
EXPECTED_VARIABLE_COUNT = 160
INPUT_INTERVAL_HOURS = 6
FORECAST_LEAD_HOURS = 6

# Canonical Prithvi-WxC MERRA-2 contract.
SURFACE_VARIABLES = (
    "EFLUX", "GWETROOT", "HFLUX", "LAI", "LWGAB", "LWGEM", "LWTUP",
    "PRECTOT", "PS", "QV2M", "SLP", "SWGNT", "SWTNT", "T2M", "TQI",
    "TQL", "TQV", "TS", "U10M", "V10M", "Z0M",
)

VERTICAL_VARIABLES = (
    "CLOUD", "H", "OMEGA", "PL", "QI", "QL", "QV", "T", "U", "V",
)

LEVELS = (
    34.0, 39.0, 41.0, 43.0, 44.0, 45.0, 48.0,
    51.0, 53.0, 56.0, 63.0, 68.0, 71.0, 72.0,
)

STATIC_SURFACE_VARIABLES = ("FRACI", "FRLAND", "FROCEAN", "PHIS")

UNITS = {
    "EFLUX": "W/m²", "GWETROOT": "", "HFLUX": "W/m²", "LAI": "m²/m²",
    "LWGAB": "W/m²", "LWGEM": "W/m²", "LWTUP": "W/m²", "PS": "Pa",
    "QV2M": "kg/kg", "SLP": "Pa", "SWGNT": "W/m²", "SWTNT": "W/m²",
    "T2M": "K", "TQI": "kg/m²", "TQL": "kg/m²", "TQV": "kg/m²",
    "TS": "K", "U10M": "m/s", "V10M": "m/s", "Z0M": "m",
    "CLOUD": "", "H": "m", "OMEGA": "Pa/s", "PL": "Pa", "PRECTOT": "kg / (m² s)",
    "QI": "kg/kg", "QL": "kg/kg", "QV": "kg/kg", "T": "K", "U": "m/s", "V": "m/s",
    "FRACI": "", "FRLAND": "", "FROCEAN": "", "PHIS": "m",
}


@dataclass(frozen=True)
class PrithviInputContract:
    model_name: str
    variable_count: int
    surface_variable_count: int
    vertical_variable_count: int
    pressure_level_count: int
    input_interval_hours: int
    forecast_lead_hours: int
    source: str


def get_input_contract() -> PrithviInputContract:
    dynamic_count = len(SURFACE_VARIABLES) + len(VERTICAL_VARIABLES) * len(LEVELS)
    return PrithviInputContract(
        model_name=MODEL_NAME,
        variable_count=dynamic_count,
        surface_variable_count=len(SURFACE_VARIABLES),
        vertical_variable_count=len(VERTICAL_VARIABLES),
        pressure_level_count=len(LEVELS),
        input_interval_hours=INPUT_INTERVAL_HOURS,
        forecast_lead_hours=FORECAST_LEAD_HOURS,
        source="MERRA-2 compatible atmospheric fields",
    )


def get_dynamic_channel_names() -> tuple[str, ...]:
    """Return the exact 160 dynamic channels in model ordering."""
    channels = list(SURFACE_VARIABLES)
    for variable in VERTICAL_VARIABLES:
        channels.extend(f"{variable}@{level:g}" for level in LEVELS)
    return tuple(channels)


def validate_variables(variables: Sequence[str]) -> dict:
    supplied = list(variables)
    expected = list(get_dynamic_channel_names())
    supplied_set = set(supplied)
    expected_set = set(expected)

    duplicates = sorted({x for x in supplied if supplied.count(x) > 1})
    missing = [x for x in expected if x not in supplied_set]
    unexpected = [x for x in supplied if x not in expected_set]

    return {
        "valid": supplied == expected,
        "expected_variable_count": len(expected),
        "supplied_variable_count": len(supplied),
        "duplicate_channels": duplicates,
        "missing_channels": missing,
        "unexpected_channels": unexpected,
        "ordering_correct": supplied == expected,
    }


def validate_dataset_metadata(
    *,
    variables: Sequence[str],
    timestamps: Sequence[datetime],
    latitudes: Sequence[float],
    longitudes: Sequence[float],
    units: Mapping[str, str],
) -> dict:
    """Validate the metadata needed before tensor construction."""
    variable_result = validate_variables(variables)
    errors: list[str] = []

    if len(timestamps) != 2:
        errors.append("exactly two input timestamps are required")
    elif timestamps[0] >= timestamps[1]:
        errors.append("input timestamps must be strictly ascending")
    elif (timestamps[1] - timestamps[0]).total_seconds() != INPUT_INTERVAL_HOURS * 3600:
        errors.append("input timestamps must be exactly 6 hours apart")

    if not latitudes or not longitudes:
        errors.append("latitude and longitude coordinates are required")

    if len(latitudes) < 2 or len(longitudes) < 2:
        errors.append("latitude and longitude grids must contain at least two points")

    for name, expected_unit in UNITS.items():
        if name in SURFACE_VARIABLES or name in VERTICAL_VARIABLES:
            actual = units.get(name)
            if actual is None:
                errors.append(f"missing unit metadata for {name}")
            elif expected_unit and actual.strip() != expected_unit:
                errors.append(f"unit mismatch for {name}: expected {expected_unit!r}, got {actual!r}")

    errors.extend(f"variable contract: {x}" for x in variable_result["missing_channels"])
    errors.extend(f"variable contract: unexpected channel {x}" for x in variable_result["unexpected_channels"])
    if variable_result["duplicate_channels"]:
        errors.append("duplicate dynamic channels are present")

    return {
        "valid": not errors,
        "errors": errors,
        "variable_validation": variable_result,
        "timestamp_count": len(timestamps),
        "latitude_points": len(latitudes),
        "longitude_points": len(longitudes),
        "required_input_interval_hours": INPUT_INTERVAL_HOURS,
        "required_forecast_lead_hours": FORECAST_LEAD_HOURS,
    }


def validate_tensor_shape(shape: Sequence[int]) -> dict:
    """Validate a preprocessed x tensor shape as [batch, time, channel, lat, lon]."""
    values = list(shape)
    errors: list[str] = []
    if len(values) != 5:
        errors.append("expected tensor shape [batch, time, channel, lat, lon]")
    else:
        if values[1] != 2:
            errors.append("time dimension must contain two input timestamps")
        if values[2] != EXPECTED_VARIABLE_COUNT:
            errors.append(f"channel dimension must be {EXPECTED_VARIABLE_COUNT}")
        if values[0] < 1 or values[3] < 1 or values[4] < 1:
            errors.append("batch and spatial dimensions must be positive")
    return {"valid": not errors, "shape": values, "errors": errors}


def validate_finite_values(values: Sequence[float]) -> dict:
    """Reject NaN/Inf values before model inference; missing-data policy is explicit."""
    non_finite = sum(1 for value in values if not isfinite(float(value)))
    return {
        "valid": non_finite == 0,
        "value_count": len(values),
        "non_finite_count": non_finite,
        "fabricated_values": False,
    }


def validate_current_imd_dataset() -> dict:
    supplied_variables = ("RAINFALL",)
    return {
        "dataset": "RF25_ind2024_rfp25.nc",
        "provider": "IMD",
        "variables": supplied_variables,
        "prithvi_compatible": False,
        "reason": (
            "The current project dataset contains rainfall only. The official "
            "Prithvi WxC contract requires 160 dynamic MERRA-2 channels. "
            "Missing atmospheric variables must be sourced from compatible "
            "data, not synthesized."
        ),
        "validation": validate_variables(supplied_variables),
    }


def print_configuration() -> None:
    contract = get_input_contract()
    print("=" * 70)
    print("INDIA CLIMATE DIGITAL TWIN - PRITHVI WxC INPUT CONTRACT")
    print("=" * 70)
    print(f"Model: {contract.model_name}")
    print(f"Provider: {MODEL_PROVIDER}")
    print(f"Dynamic channels: {contract.variable_count}")
    print(f"Surface variables: {contract.surface_variable_count}")
    print(f"Vertical variables: {contract.vertical_variable_count}")
    print(f"Pressure levels: {contract.pressure_level_count}")
    print(f"Input interval: {contract.input_interval_hours} hours")
    print(f"Forecast lead: {contract.forecast_lead_hours} hours")
    print("Current IMD compatibility:", validate_current_imd_dataset()["prithvi_compatible"])
    print("=" * 70)


if __name__ == "__main__":
    print_configuration()
