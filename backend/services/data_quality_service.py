"""Data-quality gates for the India Climate Digital Twin.

The service does not repair or invent observations. It only reports whether a
source can safely participate in the twin state and records the reason when it
cannot.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np


def validate_array(values: Any, *, variable: str, unit: str | None = None) -> dict[str, Any]:
    arr = np.asarray(values, dtype=float)
    finite = np.isfinite(arr)
    finite_values = arr[finite]
    issues: list[str] = []
    if arr.size == 0:
        issues.append("empty_array")
    if not finite.any():
        issues.append("no_finite_values")
    if np.isinf(arr).any():
        issues.append("infinite_values")
    if variable == "rainfall" and finite_values.size and np.nanmin(finite_values) < 0:
        issues.append("negative_rainfall")
    if variable == "humidity" and finite_values.size and (np.nanmin(finite_values) < 0 or np.nanmax(finite_values) > 100):
        issues.append("humidity_out_of_range")
    return {
        "variable": variable,
        "unit": unit,
        "status": "valid" if not issues else "invalid",
        "issues": issues,
        "sample_count": int(arr.size),
        "finite_count": int(finite.sum()),
        "valid_fraction": float(finite.sum() / arr.size) if arr.size else 0.0,
    }


def validate_observation(record: dict[str, Any]) -> dict[str, Any]:
    required = ["variable", "source"]
    missing = [key for key in required if not record.get(key)]
    timestamp = record.get("observation_time")
    if timestamp:
        try:
            datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        except ValueError:
            missing.append("valid_observation_time")
    return {
        "status": "valid" if not missing else "invalid",
        "missing_or_invalid": missing,
        "record": record,
    }
