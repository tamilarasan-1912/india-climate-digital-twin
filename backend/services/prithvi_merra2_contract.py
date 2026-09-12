"""MERRA-2 -> Prithvi-WxC input contract validation.

This module validates metadata and tensor structure without fabricating
missing atmospheric variables. The canonical variable names and 14 pressure
levels mirror NASA-IMPACT/Prithvi-WxC definitions.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Sequence

SURFACE_VARIABLES = (
    "EFLUX", "GWETROOT", "HFLUX", "LAI", "LWGAB", "LWGEM", "LWTUP",
    "PRECTOT", "PS", "QV2M", "SLP", "SWGNT", "SWTNT", "T2M", "TQI",
    "TQL", "TQV", "TS", "U10M", "V10M", "Z0M",
)
VERTICAL_VARIABLES = (
    "CLOUD", "H", "OMEGA", "PL", "QI", "QL", "QV", "T", "U", "V",
)
LEVELS = (34.0, 39.0, 41.0, 43.0, 44.0, 45.0, 48.0, 51.0, 53.0, 56.0, 63.0, 68.0, 71.0, 72.0)
EXPECTED_DYNAMIC_CHANNELS = len(SURFACE_VARIABLES) + len(VERTICAL_VARIABLES) * len(LEVELS)
EXPECTED_TIMESTEPS = 2
EXPECTED_INTERVAL_HOURS = 6


@dataclass(frozen=True)
class Merra2ValidationResult:
    valid: bool
    errors: tuple[str, ...]
    surface_variables: tuple[str, ...]
    vertical_variables: tuple[str, ...]
    levels: tuple[float, ...]
    dynamic_channel_count: int
    timestep_count: int

    def as_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "surface_variables": list(self.surface_variables),
            "vertical_variables": list(self.vertical_variables),
            "levels": list(self.levels),
            "dynamic_channel_count": self.dynamic_channel_count,
            "timestep_count": self.timestep_count,
            "expected_dynamic_channel_count": EXPECTED_DYNAMIC_CHANNELS,
            "expected_timestep_count": EXPECTED_TIMESTEPS,
            "expected_interval_hours": EXPECTED_INTERVAL_HOURS,
        }


def expected_dynamic_channels() -> int:
    return EXPECTED_DYNAMIC_CHANNELS


def validate_merra2_metadata(
    surface_variables: Sequence[str],
    vertical_variables: Sequence[str],
    levels: Sequence[float],
    timestamps: Sequence[datetime],
    units: Mapping[str, str] | None = None,
) -> Merra2ValidationResult:
    errors: list[str] = []
    surface = tuple(surface_variables)
    vertical = tuple(vertical_variables)
    level_values = tuple(float(x) for x in levels)

    missing_surface = sorted(set(SURFACE_VARIABLES) - set(surface))
    missing_vertical = sorted(set(VERTICAL_VARIABLES) - set(vertical))
    unexpected_surface = sorted(set(surface) - set(SURFACE_VARIABLES))
    unexpected_vertical = sorted(set(vertical) - set(VERTICAL_VARIABLES))

    if missing_surface:
        errors.append(f"Missing surface variables: {missing_surface}")
    if missing_vertical:
        errors.append(f"Missing vertical variables: {missing_vertical}")
    if unexpected_surface:
        errors.append(f"Unexpected surface variables: {unexpected_surface}")
    if unexpected_vertical:
        errors.append(f"Unexpected vertical variables: {unexpected_vertical}")
    if level_values != LEVELS:
        errors.append(f"Pressure levels do not match the Prithvi-WxC contract: {level_values}")
    if len(timestamps) != EXPECTED_TIMESTEPS:
        errors.append(f"Expected exactly {EXPECTED_TIMESTEPS} input timestamps, got {len(timestamps)}")
    elif timestamps[1] <= timestamps[0]:
        errors.append("Input timestamps must be strictly increasing")
    elif (timestamps[1] - timestamps[0]).total_seconds() != EXPECTED_INTERVAL_HOURS * 3600:
        errors.append("Input timestamps must be exactly 6 hours apart")

    if units is not None:
        required_unit_keys = set(SURFACE_VARIABLES) | set(VERTICAL_VARIABLES)
        missing_units = sorted(required_unit_keys - set(units))
        if missing_units:
            errors.append(f"Missing unit metadata for variables: {missing_units}")

    channels = len(surface) + len(vertical) * len(level_values)
    if channels != EXPECTED_DYNAMIC_CHANNELS:
        errors.append(f"Dynamic channel count is {channels}; expected {EXPECTED_DYNAMIC_CHANNELS}")

    return Merra2ValidationResult(
        valid=not errors,
        errors=tuple(errors),
        surface_variables=surface,
        vertical_variables=vertical,
        levels=level_values,
        dynamic_channel_count=channels,
        timestep_count=len(timestamps),
    )


def validate_tensor_shape(shape: Sequence[int]) -> dict:
    """Validate the dynamic tensor shape expected by the adapter.

    Expected layout is [batch, time, channels, latitude, longitude].
    """
    dims = tuple(int(x) for x in shape)
    errors: list[str] = []
    if len(dims) != 5:
        errors.append("Tensor must have 5 dimensions: [batch, time, channels, lat, lon]")
    elif dims[1] != EXPECTED_TIMESTEPS:
        errors.append(f"Expected {EXPECTED_TIMESTEPS} timesteps, got {dims[1]}")
    elif dims[2] != EXPECTED_DYNAMIC_CHANNELS:
        errors.append(f"Expected {EXPECTED_DYNAMIC_CHANNELS} channels, got {dims[2]}")
    if any(x <= 0 for x in dims):
        errors.append("All tensor dimensions must be positive")
    return {"valid": not errors, "errors": errors, "shape": list(dims)}
