"""Multi-variable twin-state utilities.

This layer provides a source-agnostic state envelope around validated variables.
It deliberately does not synthesize missing climate variables. Dataset-specific
adapters should populate observations/forecasts and this service records their
units, provenance, coverage and model metadata in one auditable state object.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from backend.services.climate_state_contract import CONTRACT_VERSION, VARIABLE_CATALOG


def build_state_envelope(
    *,
    observation_time: str,
    variables: Mapping[str, Mapping[str, Any]],
    source_state_hash: str | None = None,
    model: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a validated, provenance-aware envelope for a synchronized state.

    ``variables`` contains only values actually supplied by connected adapters.
    Each variable must provide at least ``value``, ``unit`` and ``source``.
    """
    catalog = {item["id"]: item for item in VARIABLE_CATALOG}
    normalized: dict[str, Any] = {}

    for variable_id, payload in variables.items():
        if variable_id not in catalog:
            raise ValueError(f"Variable '{variable_id}' is not defined by the climate state contract")
        if not isinstance(payload, Mapping):
            raise ValueError(f"Variable '{variable_id}' payload must be an object")
        for required in ("value", "unit", "source"):
            if required not in payload or payload[required] in (None, ""):
                raise ValueError(f"Variable '{variable_id}' is missing required field '{required}'")
        expected_unit = catalog[variable_id]["unit"]
        if str(payload["unit"]) != expected_unit:
            raise ValueError(
                f"Variable '{variable_id}' uses unit '{payload['unit']}', expected '{expected_unit}'"
            )
        normalized[variable_id] = dict(payload)

    active_ids = {item["id"] for item in VARIABLE_CATALOG if item["status"] == "active"}
    supplied_active = sorted(active_ids.intersection(normalized))
    return {
        "contract_version": CONTRACT_VERSION,
        "observation_time": observation_time,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "synchronization": {
            "status": "synchronized" if normalized else "empty",
            "active_variables_supplied": supplied_active,
            "variable_count": len(normalized),
            "source_state_hash": source_state_hash,
        },
        "variables": normalized,
        "model": dict(model) if model else None,
        "integrity": {
            "missing_variables_are_explicit": True,
            "fabricated_values_allowed": False,
            "provenance_required": True,
        },
    }


def get_active_variable_catalog() -> list[dict[str, Any]]:
    """Return only variables that are currently backed by connected data/models."""
    return [dict(item) for item in VARIABLE_CATALOG if item["status"] == "active"]
