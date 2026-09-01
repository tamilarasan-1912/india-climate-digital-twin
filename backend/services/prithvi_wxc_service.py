"""Prithvi-WxC readiness and guarded local inference integration."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

from backend.services.merra2_input_validator import discover_files, validate_dataset
from backend.services.prithvi_input_adapter import EXPECTED_VARIABLE_COUNT, FORECAST_LEAD_HOURS, INPUT_INTERVAL_HOURS, MODEL_NAME

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
    basic_input_ready = any(item.get("basic_structure_valid") and item.get("variable_count", 0) == EXPECTED_VARIABLE_COUNT for item in datasets)
    return {
        "model": MODEL_NAME,
        "repository": MODEL_REPOSITORY,
        "provider": "IBM / NASA",
        "purpose": "6-hour weather forecasting / autoregressive rollout",
        "contract": {"input_timestamps": 2, "variable_count": EXPECTED_VARIABLE_COUNT, "input_interval_hours": INPUT_INTERVAL_HOURS, "forecast_lead_hours": FORECAST_LEAD_HOURS},
        "checkpoint": {"path": str(checkpoint), "present": checkpoint.exists(), "expected_size_gb": MODEL_SIZE_GB},
        "runtime": {"python_torch": torch_installed, "terratorch": terratorch_installed},
        "merra2": {"files_found": len(merra_files), "input_ready": basic_input_ready, "datasets": datasets},
        "inference_ready": bool(checkpoint.exists() and terratorch_installed and torch_installed and basic_input_ready),
        "status": "ready" if checkpoint.exists() and terratorch_installed and torch_installed and basic_input_ready else "blocked",
        "blockers": _get_blockers(checkpoint, terratorch_installed, torch_installed, basic_input_ready),
    }


def _get_blockers(checkpoint: Path, terratorch: bool, torch: bool, input_ready: bool) -> list[str]:
    blockers = []
    if not checkpoint.exists(): blockers.append("Prithvi WxC rollout checkpoint is not installed locally.")
    if not torch: blockers.append("PyTorch is not installed in the active environment.")
    if not terratorch: blockers.append("TerraTorch is not installed in the active environment.")
    if not input_ready: blockers.append("A validated MERRA-2 dataset with exactly 160 atmospheric variables is not available.")
    return blockers


def validate_prithvi_inputs() -> dict[str, Any]:
    status = get_prithvi_wxc_status()
    return {"model": status["model"], "contract": status["contract"], "merra2": status["merra2"], "checkpoint": status["checkpoint"], "runtime": status["runtime"], "input_ready": status["merra2"]["input_ready"], "inference_ready": status["inference_ready"], "blockers": status["blockers"]}


def run_local_inference() -> dict[str, Any]:
    """Load the official model only after all assets pass readiness checks."""
    status = get_prithvi_wxc_status()
    if not status["inference_ready"]:
        return {
            "status": "WAITING_FOR_MODEL_ASSETS",
            "model": MODEL_NAME,
            "forecast_generated": False,
            "blockers": status["blockers"],
        }
    try:
        from terratorch.registry import BACKBONE_REGISTRY
        model = BACKBONE_REGISTRY.build(MODEL_REPOSITORY, ckpt_path=str(_checkpoint_path()))
    except ImportError as error:
        raise RuntimeError("TerraTorch is required for Prithvi WxC inference.") from error
    except Exception as error:
        raise RuntimeError(f"Prithvi WxC checkpoint/model load failed: {error}") from error
    return {"status": "model_loaded", "model": MODEL_NAME, "checkpoint": str(_checkpoint_path()), "model_class": type(model).__name__, "forecast_generated": False, "next_step": "connect the validated two-timestamp MERRA-2 tensor to the official rollout forward path"}
