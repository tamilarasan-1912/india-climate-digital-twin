"""Forecast contract shared by baseline and future AI forecast engines."""
from __future__ import annotations

from typing import Any


def build_forecast_contract(*, scope: str, model: str, lead_hours: int, variables: dict[str, Any], status: str, provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "scope": scope,
        "type": "forecast",
        "model": model,
        "lead_time_hours": lead_hours,
        "variables": variables,
        "status": status,
        "uncertainty": {"status": "not_calibrated"},
        "provenance": provenance or {},
        "scientific_note": "Forecast values must originate from a validated model run; this contract never substitutes synthetic values for missing model output.",
    }
