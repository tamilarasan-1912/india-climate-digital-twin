"""Readiness gate for the real Prithvi-WxC forecast path."""
from __future__ import annotations
from typing import Any

REQUIRED_MERRA_VARIABLE_COUNT = 160


def assess_prithvi_readiness(validation: dict[str, Any]) -> dict[str, Any]:
    variables = validation.get("variables", validation.get("variable_count", 0))
    if isinstance(variables, list):
        count = len(variables)
    else:
        try:
            count = int(variables)
        except (TypeError, ValueError):
            count = 0
    ready = bool(validation.get("valid")) and count >= REQUIRED_MERRA_VARIABLE_COUNT
    return {
        "status": "ready" if ready else "blocked",
        "required_merra2_variables": REQUIRED_MERRA_VARIABLE_COUNT,
        "validated_variable_count": count,
        "model": "ibm-nasa-geospatial/Prithvi-WxC-1.0-2300M-rollout",
        "reason": "Validated 160-variable MERRA-2 contract is required before inference." if not ready else "Input contract is sufficient for the next inference stage.",
        "weights": "external_runtime_required",
        "synthetic_forecast_allowed": False,
    }
