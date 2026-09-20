"""Application-level Prithvi-WxC forecast adapter.

This service exposes a stable response contract for the UI/API. It delegates
model readiness to the guarded inference service and never fabricates forecast
values when the model assets are unavailable.
"""
from __future__ import annotations

from typing import Any

from backend.services.prithvi_wxc_inference_service import PrithviWxCRunner


def get_prithvi_forecast_status() -> dict[str, Any]:
    runner = PrithviWxCRunner(
        checkpoint="models/prithvi-wxc/prithvi.wxc.rollout.2300m.v1.pt",
        input_tensor="backend/data/merra2/prepared/prithvi_wxc_input.npy",
    )
    status = runner.status()
    return {
        "status": status.status,
        "model": status.model,
        "forecast_generated": False,
        "checkpoint_present": status.checkpoint_present,
        "input_present": status.input_present,
        "message": status.message,
    }


def generate_prithvi_forecast() -> dict[str, Any]:
    runner = PrithviWxCRunner(
        checkpoint="models/prithvi-wxc/prithvi.wxc.rollout.2300m.v1.pt",
        input_tensor="backend/data/merra2/prepared/prithvi_wxc_input.npy",
    )
    return runner.predict()
