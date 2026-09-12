"""Prithvi WxC readiness and official rollout integration."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

import xarray as xr

from backend.services.merra2_input_validator import discover_files, validate_dataset
from backend.services.prithvi_input_adapter import (
    EXPECTED_VARIABLE_COUNT,
    FORECAST_LEAD_HOURS,
    INPUT_INTERVAL_HOURS,
    MODEL_NAME,
)
from backend.services.prithvi_official_runtime import get_official_runtime_status, run_official_rollout

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

    torch_installed = importlib.util.find_spec("torch") is not None
    official = get_official_runtime_status()
    basic_input_ready = any(
        item.get("basic_structure_valid") and item.get("variable_count", 0) >= EXPECTED_VARIABLE_COUNT
        for item in datasets
    )

    blockers = _get_blockers(checkpoint, torch_installed, basic_input_ready, official)
    inference_ready = bool(torch_installed and official["ready"])

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
            "note": "Official runtime may download/manage its own Hugging Face checkpoint cache.",
        },
        "runtime": {
            "python_torch": torch_installed,
            "official_prithvi_package": official["official_package_installed"],
            "official_runtime": official,
        },
        "merra2": {
            "files_found": len(merra_files),
            "input_ready": basic_input_ready,
            "datasets": datasets,
        },
        "inference_ready": inference_ready,
        "status": "ready" if inference_ready else "blocked",
        "blockers": blockers,
    }


def _get_blockers(
    checkpoint: Path,
    torch: bool,
    input_ready: bool,
    official: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not torch:
        blockers.append("PyTorch is not installed in the active environment.")
    if not official["official_package_installed"]:
        blockers.append("Official NASA-IMPACT PrithviWxC package is not installed.")
    if not official["ready"]:
        missing = [name for name, present in official["scalers_present"].items() if not present]
        if missing:
            blockers.append("Required official climatology/scaler files are missing: " + ", ".join(missing))
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


def _infer_time_range_from_local_merra() -> tuple[str, str]:
    """Infer two real six-hour input timestamps from the newest local NetCDF."""
    candidates = sorted(discover_files(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise RuntimeError("Cannot infer Prithvi-WxC timestamps: no local MERRA-2 NetCDF files were found.")
    for path in candidates:
        try:
            with xr.open_dataset(path) as ds:
                for name in ("time", "TIME"):
                    if name in ds.coords or name in ds.dims:
                        values = ds[name].values
                        if len(values) < 2:
                            continue
                        end = values[-1]
                        start = end - __import__("numpy").timedelta64(6, "h")
                        if start in values:
                            return str(start), str(end)
        except Exception:
            continue
    raise RuntimeError("Cannot infer two six-hour-separated timestamps from local MERRA-2 data.")


def run_local_inference(
    time_start: str | None = None,
    time_end: str | None = None,
    lead_time_hours: int = 6,
) -> dict[str, Any]:
    """Run the official NASA-IMPACT Prithvi-WxC rollout pipeline.

    If timestamps are omitted by the API caller, the service derives them from
    the newest real local MERRA-2 file; it never fabricates a forecast state.
    """
    start = time_start or os.getenv("PRITHVI_WXC_TIME_START")
    end = time_end or os.getenv("PRITHVI_WXC_TIME_END")
    if not start or not end:
        start, end = _infer_time_range_from_local_merra()

    result = run_official_rollout(start, end, lead_time_hours)
    tensor = result.pop("forecast_tensor")
    result["forecast_tensor_shape"] = list(tensor.shape)
    result["forecast_tensor_device"] = str(tensor.device)
    result["forecast_values_materialized"] = True
    result["input_time_start"] = start
    result["input_time_end"] = end
    return result
