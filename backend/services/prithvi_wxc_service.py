"""Prithvi WxC readiness and optional local inference integration.

The repository never stores the 28.4 GB Prithvi WxC checkpoint. The service
therefore separates scientific readiness checks from optional inference.

The official rollout checkpoint is intended for forecasting and expects two
MERRA-2 timestamps, 160 atmospheric variables, a 6-hour input interval and a
6-hour forecast lead.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from backend.services.merra2_input_validator import discover_files, validate_dataset
from backend.services.prithvi_input_adapter import (
    EXPECTED_VARIABLE_COUNT,
    FORECAST_LEAD_HOURS,
    INPUT_INTERVAL_HOURS,
    MODEL_NAME,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models" / "prithvi-wxc"
DEFAULT_CHECKPOINT = MODEL_DIR / "prithvi.wxc.rollout.2300m.v1.pt"
MODEL_REPOSITORY = "ibm-nasa-geospatial/Prithvi-WxC-1.0-2300M-rollout"
MODEL_SIZE_GB = 28.4


def _checkpoint_path() -> Path:
    return Path(os.getenv("PRITHVI_WXC_CHECKPOINT", str(DEFAULT_CHECKPOINT)))


def get_prithvi_wxc_status() -> dict[str, Any]:
    checkpoint = _checkpoint_path()
    merra_files = discover_files()
    datasets = []
    for path in merra_files:
        try:
            datasets.append(validate_dataset(path))
        except Exception as error:
            datasets.append({"file": str(path), "valid": False, "error": str(error)})

    terratorch_installed = importlib.util.find_spec("terratorch") is not None
    torch_installed = importlib.util.find_spec("torch") is not None
    basic_input_ready = any(
        item.get("basic_structure_valid") and item.get("variable_count", 0) >= EXPECTED_VARIABLE_COUNT
        for item in datasets
    )

    return {
        "model": MODEL_NAME,
        "repository": MODEL_REPOSITORY,
        "provider": "IBM / NASA",
        "purpose": "6-hour weather forecasting / autoregressive rollout",
        "contract": {
            "input_timestamps": 2,
            "variable_count": EXPECTED_VARIABLE_COUNT,
            "input_interval_hours": INPUT_INTERVAL_HOURS,
            "forecast_lead_hours": FORECAST_LEAD_HOURS,
        },
        "checkpoint": {
            "path": str(checkpoint),
            "present": checkpoint.exists(),
            "expected_size_gb": MODEL_SIZE_GB,
        },
        "runtime": {
            "python_torch": torch_installed,
            "terratorch": terratorch_installed,
        },
        "merra2": {
            "files_found": len(merra_files),
            "input_ready": basic_input_ready,
            "datasets": datasets,
        },
        "inference_ready": bool(checkpoint.exists() and terratorch_installed and torch_installed and basic_input_ready),
        "status": "ready" if checkpoint.exists() and terratorch_installed and torch_installed and basic_input_ready else "blocked",
        "blockers": _get_blockers(checkpoint, terratorch_installed, torch_installed, basic_input_ready),
    }


def _get_blockers(checkpoint: Path, terratorch: bool, torch: bool, input_ready: bool) -> list[str]:
    blockers: list[str] = []
    if not checkpoint.exists():
        blockers.append("Prithvi WxC rollout checkpoint is not installed locally.")
    if not torch:
        blockers.append("PyTorch is not installed in the active environment.")
    if not terratorch:
        blockers.append("TerraTorch is not installed in the active environment.")
    if not input_ready:
        blockers.append("A validated MERRA-2 dataset with the required 160-variable structure is not available.")
    return blockers


def validate_prithvi_inputs() -> dict[str, Any]:
    status = get_prithvi_wxc_status()
    return {
        "model": status["model"],
        "contract": status["contract"],
        "merra2": status["merra2"],
        "checkpoint": status["checkpoint"],
        "runtime": status["runtime"],
        "input_ready": status["merra2"]["input_ready"],
        "inference_ready": status["inference_ready"],
        "blockers": status["blockers"],
    }


def run_local_inference() -> dict[str, Any]:
    """Run the model only when all prerequisites are actually present.

    This method intentionally refuses to fabricate a forecast. The exact
    MERRA-2 preprocessing and tensor construction must be performed by the
    TerraTorch/MERRA-2 pipeline before model.forward is invoked.
    """
    status = get_prithvi_wxc_status()
    if not status["inference_ready"]:
        raise RuntimeError(
            "Prithvi WxC inference is blocked: " + "; ".join(status["blockers"])
        )

    try:
        from terratorch.registry import BACKBONE_REGISTRY
    except ImportError as error:
        raise RuntimeError("TerraTorch is required for Prithvi WxC inference.") from error

    checkpoint = str(_checkpoint_path())
    model = BACKBONE_REGISTRY.build(
        MODEL_REPOSITORY,
        ckpt_path=checkpoint,
    )

    return {
        "status": "model_loaded",
        "model": MODEL_NAME,
        "checkpoint": checkpoint,
        "model_class": type(model).__name__,
        "message": "Checkpoint loaded successfully. Feed a TerraTorch-preprocessed two-timestamp MERRA-2 tensor to the model before exposing forecast output.",
        "next_step": "wire the validated MERRA-2 dataloader/tensor contract into model.forward",
    }
