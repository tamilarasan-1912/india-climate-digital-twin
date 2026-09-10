"""Transparent observation/reanalysis state assimilation.

The service implements a conservative weighted fusion primitive. It never
creates a value when no source exists and returns the source weights and spread
used for every fused variable.
"""
from __future__ import annotations

from typing import Any
import math


def assimilate_variable(observations: list[dict[str, Any]]) -> dict[str, Any]:
    valid = []
    for item in observations:
        value = item.get("value")
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value):
            continue
        weight = float(item.get("weight", 1.0))
        if weight > 0:
            valid.append({**item, "value": value, "weight": weight})
    if not valid:
        return {"status": "no_data", "value": None, "uncertainty": None, "sources": []}
    total = sum(x["weight"] for x in valid)
    fused = sum(x["value"] * x["weight"] for x in valid) / total
    variance = sum(x["weight"] * (x["value"] - fused) ** 2 for x in valid) / total
    return {
        "status": "assimilated" if len(valid) > 1 else "single_source",
        "value": fused,
        "uncertainty": variance ** 0.5,
        "sources": [{"source": x.get("source"), "weight": x["weight"], "value": x["value"]} for x in valid],
        "method": "weighted observation fusion; no learned correction",
    }


def assimilate_state(source_states: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    result = {variable: assimilate_variable(items) for variable, items in source_states.items()}
    return {
        "status": "assimilated" if any(v["status"] in {"assimilated", "single_source"} for v in result.values()) else "no_data",
        "variables": result,
        "policy": "only supplied validated sources are fused; missing variables remain no_data",
    }
