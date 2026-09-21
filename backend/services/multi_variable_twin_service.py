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


def _source_availability() -> dict[str, str]:
    """Map each declared source to its live availability.

    The variable catalog describes design intent. Whether a variable is
    actually backed by connected data is a runtime fact, so it is resolved
    here on every call instead of being asserted by the static catalog.
    """
    availability = {"IMD RF25": "available", "rainfall hazard engine": "available"}
    try:
        from backend.services.prithvi_wxc_service import get_prithvi_wxc_status

        ready = bool(get_prithvi_wxc_status().get("inference_ready"))
    except Exception:
        ready = False
    availability["NASA-IMPACT Prithvi-WxC rollout"] = "available" if ready else "blocked"
    return availability


def get_active_variable_catalog() -> list[dict[str, Any]]:
    """Return only variables currently backed by connected data or models.

    A variable whose source is blocked at runtime is excluded, so the endpoint
    cannot advertise atmospheric variables while the model that produces them
    is unavailable.
    """
    availability = _source_availability()
    active: list[dict[str, Any]] = []
    for item in VARIABLE_CATALOG:
        if item["status"] != "active":
            continue
        state = availability.get(item.get("source") or "", "provider_required")
        if state != "available":
            continue
        active.append({**item, "availability": state})
    return active


def get_variable_availability_report() -> dict[str, Any]:
    """Report every contract variable with its declared and runtime status."""
    availability = _source_availability()
    variables = []
    for item in VARIABLE_CATALOG:
        source = item.get("source")
        runtime = availability.get(source or "", "provider_required") if source else "planned"
        if item["status"] == "planned":
            runtime = "planned"
        variables.append({**item, "availability": runtime})
    return {
        "contract_version": CONTRACT_VERSION,
        "available_variable_count": sum(1 for v in variables if v["availability"] == "available"),
        "unavailable_variables": [v["id"] for v in variables if v["availability"] != "available"],
        "variables": variables,
    }
