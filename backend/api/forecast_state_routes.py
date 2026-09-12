"""API helpers for forecast-state and hazard inspection."""

from __future__ import annotations

from typing import Any

from backend.services.forecast_state_service import build_forecast_state, build_hazard_summary


def summarize_forecast_output(output: Any, *, forecast_time: str, input_time: str, state_hash: str | None = None) -> dict[str, Any]:
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
