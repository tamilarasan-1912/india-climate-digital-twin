"""Official Prithvi-WxC rollout runtime adapter.

This module deliberately delegates preprocessing/model execution to the upstream
NASA-IMPACT Prithvi-WxC package instead of reimplementing its scientific
pipeline. The rollout model requires two MERRA-2 timestamps, official
climatology/scalers, static features and a six-hour forecasting step.

No forecast is returned unless the official runtime, required MERRA-2 files,
climatology and model weights are actually available.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = PROJECT_ROOT / "models" / "prithvi-wxc" / "data"

SURFACE_VARS = [
    "EFLUX", "GWETROOT", "HFLUX", "LAI", "LWGAB", "LWGEM", "LWTUP",
    "PS", "QV2M", "SLP", "SWGNT", "SWTNT", "T2M", "TQI", "TQL", "TQV",
    "TS", "U10M", "V10M", "Z0M",
]
STATIC_SURFACE_VARS = ["FRACI", "FRLAND", "FROCEAN", "PHIS"]
VERTICAL_VARS = ["CLOUD", "H", "OMEGA", "PL", "QI", "QL", "QV", "T", "U", "V"]
LEVELS = [34.0, 39.0, 41.0, 43.0, 44.0, 45.0, 48.0, 51.0, 53.0, 56.0, 63.0, 68.0, 71.0, 72.0]


def _data_dir() -> Path:
    return Path(os.getenv("PRITHVI_WXC_DATA_DIR", str(DEFAULT_DATA_DIR)))


def _surface_dir() -> Path:
    return Path(os.getenv("PRITHVI_WXC_MERRA2_SURFACE_DIR", str(_data_dir() / "merra-2")))


def _vertical_dir() -> Path:
    return Path(os.getenv("PRITHVI_WXC_MERRA2_VERTICAL_DIR", str(_data_dir() / "merra-2")))


def _climate_surface_dir() -> Path:
    return Path(os.getenv("PRITHVI_WXC_CLIM_SURFACE_DIR", str(_data_dir() / "climatology")))


def _climate_vertical_dir() -> Path:
    return Path(os.getenv("PRITHVI_WXC_CLIM_VERTICAL_DIR", str(_data_dir() / "climatology")))


def get_official_runtime_status() -> dict[str, Any]:
    package_installed = importlib.util.find_spec("PrithviWxC") is not None
    data_dir = _data_dir()
    surface_dir = _surface_dir()
    vertical_dir = _vertical_dir()
    clim_surface = _climate_surface_dir()
    clim_vertical = _climate_vertical_dir()
    required_scalers = [
        clim_surface / "musigma_surface.nc",
        clim_vertical / "musigma_vertical.nc",
        clim_surface / "anomaly_variance_surface.nc",
        clim_vertical / "anomaly_variance_vertical.nc",
    ]
    return {
        "official_package_installed": package_installed,
        "data_dir": str(data_dir),
        "surface_dir": str(surface_dir),
        "vertical_dir": str(vertical_dir),
        "climatology_surface_dir": str(clim_surface),
        "climatology_vertical_dir": str(clim_vertical),
        "scalers_present": {p.name: p.exists() for p in required_scalers},
        "surface_netcdf_count": len(list(surface_dir.glob("*.nc"))) if surface_dir.exists() else 0,
        "vertical_netcdf_count": len(list(vertical_dir.glob("*.nc"))) if vertical_dir.exists() else 0,
        "ready": package_installed and all(p.exists() for p in required_scalers),
    }


def run_official_rollout(
    time_start: str,
    time_end: str,
    lead_time_hours: int = 6,
) -> dict[str, Any]:
    """Execute one or more official Prithvi-WxC rollout steps.

    The upstream rollout dataloader is used for file discovery, climatology,
    static features, normalization and target construction. The upstream
    ``rollout_iter`` helper then performs autoregressive inference.
    """
    status = get_official_runtime_status()
    if not status["official_package_installed"]:
        raise RuntimeError(
            "Official PrithviWxC package is not installed. Install the NASA-IMPACT "
            "Prithvi-WxC package before enabling model inference."
        )
    missing = [name for name, present in status["scalers_present"].items() if not present]
    if missing:
        raise RuntimeError("Required Prithvi-WxC climatology files are missing: " + ", ".join(missing))

    try:
        import torch
        from PrithviWxC.configs import load_model
        from PrithviWxC.dataloaders.merra2_rollout import Merra2RolloutDataset, preproc
        from PrithviWxC.rollout import rollout_iter
    except ImportError as error:
        raise RuntimeError(f"Official Prithvi-WxC runtime dependencies are incomplete: {error}") from error

    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    input_time = -6
    if lead_time_hours < 1 or lead_time_hours % 6 != 0:
        raise ValueError("Prithvi-WxC rollout lead time must be a positive multiple of 6 hours.")

    dataset = Merra2RolloutDataset(
        time_range=(time_start, time_end),
        lead_time=lead_time_hours,
        input_time=input_time,
        data_path_surface=_surface_dir(),
        data_path_vertical=_vertical_dir(),
        climatology_path_surface=_climate_surface_dir(),
        climatology_path_vertical=_climate_vertical_dir(),
        surface_vars=SURFACE_VARS,
        static_surface_vars=STATIC_SURFACE_VARS,
        vertical_vars=VERTICAL_VARS,
        levels=LEVELS,
        positional_encoding="fourier",
    )
    if len(dataset) == 0:
        raise RuntimeError("Prithvi-WxC found no valid MERRA-2 rollout sample for the requested time range.")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model("large_rollout", data_dir, load_weights=True)
    model = model.to(device)
    model.eval()

    data = next(iter(dataset))
    padding = {"level": [0, 0], "lat": [0, -1], "lon": [0, 0]}
    batch = preproc([data], padding)
    for key, value in batch.items():
        if isinstance(value, torch.Tensor):
            batch[key] = value.to(device)

    with torch.no_grad():
        output = rollout_iter(dataset.nsteps, model, batch)

    output_cpu = output.detach().cpu()
    if not torch.isfinite(output_cpu).all():
        raise RuntimeError("Prithvi-WxC returned non-finite forecast values.")

    return {
        "status": "forecast_generated",
        "model": "prithvi.wxc.rollout.2300m.v1",
        "device": str(device),
        "input_time_hours": 6,
        "lead_time_hours": lead_time_hours,
        "rollout_steps": int(dataset.nsteps),
        "output_shape": list(output_cpu.shape),
        "output_dtype": str(output_cpu.dtype),
        "target_time": str(data.get("target_time", "")),
        "source": "NASA-IMPACT Prithvi-WxC official rollout pipeline",
        "forecast_tensor": output_cpu,
    }
