"""Asset-gated Prithvi-WxC inference service.

The service exposes a stable application interface while refusing to return
fabricated forecasts when the official checkpoint/preprocessing assets are
not installed. Actual model execution is isolated behind a runner interface.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class InferenceStatus:
    status: str
    model: str
    checkpoint_present: bool
    input_present: bool
    message: str


class PrithviWxCRunner:
    """Guarded runner for the official Prithvi-WxC rollout checkpoint."""

    def __init__(self, checkpoint: str | Path, input_tensor: str | Path):
        self.checkpoint = Path(checkpoint)
        self.input_tensor = Path(input_tensor)

    def status(self) -> InferenceStatus:
        checkpoint_present = self.checkpoint.exists()
        input_present = self.input_tensor.exists()
        if not checkpoint_present:
            return InferenceStatus(
                status="WAITING_FOR_MODEL_ASSETS",
                model="Prithvi-WxC-1.0-2300M-rollout",
                checkpoint_present=False,
                input_present=input_present,
                message="Official Prithvi-WxC checkpoint is not installed; no forecast is generated.",
            )
        if not input_present:
            return InferenceStatus(
                status="WAITING_FOR_INPUT_ASSETS",
                model="Prithvi-WxC-1.0-2300M-rollout",
                checkpoint_present=True,
                input_present=False,
                message="Validated Prithvi-WxC input tensor is not available; no forecast is generated.",
            )
        return InferenceStatus(
            status="READY_FOR_INFERENCE",
            model="Prithvi-WxC-1.0-2300M-rollout",
            checkpoint_present=True,
            input_present=True,
            message="Model and validated input assets are available. Actual inference runner can be enabled.",
        )

    def predict(self) -> dict[str, Any]:
        state = self.status()
        if state.status != "READY_FOR_INFERENCE":
            return {
                "status": state.status,
                "model": state.model,
                "forecast_generated": False,
                "checkpoint_present": state.checkpoint_present,
                "input_present": state.input_present,
                "message": state.message,
            }
        raise NotImplementedError(
            "Official Prithvi-WxC rollout execution must be wired to the NASA/IBM reference implementation and verified model assets before production inference."
        )
