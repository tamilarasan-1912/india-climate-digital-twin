"""Digital-twin synchronization cycle.

The cycle is intentionally deterministic: discover validated observations,
assemble the state, derive hazards, and expose freshness/coverage. External
connectors can feed the documented data directories without changing the twin
contract.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from backend.services.climate_state_service import build_climate_state
from backend.services.multi_hazard_service import calculate_hazards


def synchronize(target_date: str | None = None) -> dict[str, Any]:
    state = build_climate_state(target_date)
    hazards = calculate_hazards(state)
    available = state["twin_state"]["available_variables"]
    total = state["synchronization"]["total_variable_count"]
    return {
        "status": "synchronized" if available else "degraded",
        "synchronized_at": datetime.now(timezone.utc).isoformat(),
        "coverage": {"available_variables": available, "available_count": len(available), "total_count": total},
        "twin_state": state["twin_state"],
        "risk_state": hazards,
        "next_cycle": "Run again after new validated observations are ingested.",
    }
