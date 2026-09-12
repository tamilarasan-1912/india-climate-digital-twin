"""API helpers for real Prithvi-WxC forecast-state generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.services.forecast_state_service import build_forecast_state, build_hazard_summary
from backend.services.prithvi_official_runtime import run_official_rollout


def summarize_forecast_output(
    output: Any,
    *,
    forecast_time: str,
    input_time: str,
    state_hash: str | None = None,
) -> dict[str, Any]:
    state = build_forecast_state(
        output,
        forecast_time=forecast_time,
        input_time=input_time,
        source_state_hash=state_hash,
    )
    return {
        "status": "forecast_state_created",
        "state": state,
        "hazards": build_hazard_summary(state),
    }


def generate_prithvi_forecast(
    time_start: str,
    time_end: str,
    lead_time_hours: int = 6,
) -> dict[str, Any]:
    """Run official Prithvi-WxC and convert its output into twin state."""
    result = run_official_rollout(time_start, time_end, lead_time_hours)
    forecast_time = result["target_time"]
    if not forecast_time or forecast_time == "None":
        forecast_time = datetime.now(timezone.utc).isoformat()

    summary = summarize_forecast_output(
        result["forecast_tensor"],
        forecast_time=str(forecast_time),
        input_time=time_start,
    )
    return {
        "status": "prithvi_forecast_ready",
        "runtime": {key: value for key, value in result.items() if key not in {"forecast_tensor", "all_outputs"}},
        **summary,
    }
