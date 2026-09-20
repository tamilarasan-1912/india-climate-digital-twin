"""Government operations/readiness summary for the India Climate Digital Twin."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.services.data_catalog_service import get_data_catalog
from backend.services.digital_twin_service import get_system_health
from backend.services.governance_service import security_status
from backend.services.prithvi_wxc_service import get_prithvi_wxc_status


def _severity(status: str) -> str:
    return {"operational": "normal", "ready": "normal", "connected": "normal", "partial": "warning", "planned_operational": "warning", "asset_gated": "warning", "degraded": "warning", "offline": "critical"}.get(status, "info")


def get_operations_status() -> dict[str, Any]:
    """Return a transparent control-room status; never manufacture availability."""
    system = get_system_health()
    catalog = get_data_catalog()
    prithvi = get_prithvi_wxc_status()
    security = security_status()

    connected = [entry for entry in catalog["entries"] if entry["status"] == "connected"]
    warnings = [entry["id"] for entry in catalog["entries"] if entry["status"] not in {"connected", "ready"}]

    system_status = str(system.get("status", "unknown"))
    if system_status in {"healthy", "online", "operational"}:
        overall = "operational"
    elif system_status in {"degraded", "partial"}:
        overall = "degraded"
    else:
        overall = "attention_required"

    return {
        "scope": "India",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall,
        "severity": _severity(overall),
        "system": system,
        "data": {
            "catalog_entries": len(catalog["entries"]),
            "connected_sources": len(connected),
            "connected_source_ids": [entry["id"] for entry in connected],
            "attention_source_ids": warnings,
        },
        "forecast": {
            "prithvi_wxc": prithvi,
            "synthetic_forecast": False,
        },
        "security": security,
        "operator_actions": [
            "Review any source marked partial, planned_operational, contract_ready or asset_gated.",
            "Verify observation freshness before issuing an operational decision.",
            "Use only validated forecast outputs; do not treat readiness as a forecast.",
        ],
    }
