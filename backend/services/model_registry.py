"""Model registry for the India Climate Digital Twin.

Every model that can influence a climate value must be registered with an
explicit identity, version, input contract, output contract, validation basis
and inference status. Registration is metadata only: a registered model with
unmet dependencies reports ``blocked`` or ``provider_required`` rather than
producing values.
"""
from __future__ import annotations

from typing import Any

MODEL_REGISTRY_VERSION = "1.0.0"

INFERENCE_STATES = (
    "operational",
    "available",
    "validation_required",
    "blocked",
    "provider_required",
)


def _model(
    *,
    model_id: str,
    name: str,
    kind: str,
    version: str,
    provider: str,
    status: str,
    purpose: str,
    input_contract: dict[str, Any],
    output_contract: dict[str, Any],
    validation: dict[str, Any],
    inference_status: str,
    outputs_produced: bool,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if inference_status not in INFERENCE_STATES:
        raise ValueError(f"Unsupported inference status '{inference_status}'")
    return {
        "model_id": model_id,
        "name": name,
        "type": kind,
        "version": version,
        "provider": provider,
        "status": status,
        "purpose": purpose,
        "input_contract": input_contract,
        "output_contract": output_contract,
        "validation": validation,
        "inference_status": inference_status,
        "outputs_produced": outputs_produced,
        "scientific_note": (
            "A registered model is not an operating model. Inference status "
            "reflects verified dependencies, not configuration alone."
        ),
        **(metadata or {}),
    }


def _imd_baseline() -> dict[str, Any]:
    from backend.services.baseline_forecast_service import generate_test_forecasts, calculate_metrics

    metric: dict[str, Any] | None = None
    try:
        forecasts = generate_test_forecasts()
        metric = calculate_metrics(forecasts) if forecasts else None
    except Exception as error:  # dataset absent -> explicit unavailable validation
        metric = {"status": "unavailable", "reason": str(error)}

    return _model(
        model_id="imd-rainfall-moving-average",
        name="IMD rainfall baseline",
        kind="statistical baseline",
        version="7-day moving average (baseline-1.0.0)",
        provider="IMD",
        status="active",
        purpose="Transparent benchmark for rainfall forecasting; not a physical or AI weather model.",
        input_contract={"variables": ["precipitation"], "unit": "mm", "window_days": 7, "source": "IMD RF25"},
        output_contract={"variables": ["rainfall_mm"], "unit": "mm", "horizon_days": "1-14"},
        validation={
            "method": "walk-forward evaluation over a held-out period with no future information",
            "metrics": metric,
            "ground_truth": "IMD observed rainfall",
        },
        inference_status="operational" if metric and "mae_mm" in metric else "blocked",
        outputs_produced=bool(metric and "mae_mm" in metric),
        metadata={
            "display_name": "IMD rainfall baseline",
            "model": "IMD rainfall baseline",
            "reported_status": "active",
            "metrics_endpoint": "/api/validation",
            "is_ai_model": False,
        },
    )


def _rainfall_hazard() -> dict[str, Any]:
    from backend.services.rainfall_service import read_dataset

    available = False
    reason = None
    try:
        with read_dataset() as dataset:
            available = "RAINFALL" in dataset
    except Exception as error:
        reason = str(error)

    return _model(
        model_id="rainfall-hazard-screen",
        name="Rainfall hazard screening engine",
        kind="deterministic hazard rule",
        version="rainfall-hazard-1.0.0",
        provider="India Climate Digital Twin",
        status="active" if available else "unavailable",
        purpose="Threshold-based rainfall hazard screening used by the risk and twin layers.",
        input_contract={"variables": ["precipitation"], "unit": "mm", "source": "IMD RF25"},
        output_contract={"variables": ["hazard_score", "risk_category"], "unit": "0-100"},
        validation={
            "method": "structural and distribution checks",
            "ground_truth": None,
            "note": "No calibrated impact validation exists; the score is a screening index.",
        },
        inference_status="operational" if available else "blocked",
        outputs_produced=available,
        metadata={"model": "Rainfall hazard screening engine", "reported_status": "active" if available else "unavailable", "blocked_reason": reason, "is_ai_model": False},
    )


def _prithvi_eo() -> dict[str, Any]:
    return _model(
        model_id="prithvi-eo-v2-tiny",
        name="Prithvi-EO V2 tiny",
        kind="earth observation foundation model",
        version="Prithvi-EO-V2-tiny-TL",
        provider="IBM / NASA",
        status="feature extraction available",
        purpose="Earth-observation feature extraction for the Chennai fused twin state.",
        input_contract={"variables": ["HLS/co-registered multispectral scenes"], "spatial": "Chennai AOI"},
        output_contract={"variables": ["scene/temporal embeddings"], "note": "Embeddings are inputs to a deterministic state projection, not forecasts."},
        validation={"method": "none for forecasting", "note": "Not calibrated for forecasting; used for representation only."},
        inference_status="available",
        outputs_produced=True,
        metadata={"model": "Prithvi-EO V2 tiny", "reported_status": "feature extraction available", "is_ai_model": True},
    )


def _prithvi_wxc() -> dict[str, Any]:
    from backend.services.prithvi_input_adapter import EXPECTED_VARIABLE_COUNT, FORECAST_LEAD_HOURS, INPUT_INTERVAL_HOURS, MODEL_NAME

    try:
        from backend.services.prithvi_wxc_service import get_prithvi_wxc_status

        live = get_prithvi_wxc_status()
        inference_status = "operational" if live.get("inference_ready") else "blocked"
        blockers = live.get("blockers", [])
    except Exception as error:
        live = {"status": "blocked"}
        inference_status = "blocked"
        blockers = [str(error)]

    return _model(
        model_id="prithvi-wxc-rollout",
        name=MODEL_NAME,
        kind="atmospheric foundation model (rollout)",
        version="Prithvi-WxC-1.0-2300M-rollout",
        provider="IBM / NASA",
        status=live.get("status", "blocked"),
        purpose="6-hour autoregressive weather forecasting / rollout.",
        input_contract={
            "variables_count": EXPECTED_VARIABLE_COUNT,
            "input_timestamps": 2,
            "interval_hours": INPUT_INTERVAL_HOURS,
            "source": "MERRA-2 compatible surface + vertical fields plus official climatology scalers",
        },
        output_contract={
            "variables": ["atmospheric state fields"],
            "lead_hours": FORECAST_LEAD_HOURS,
            "note": "Model owns normalization/residual-climatology transformation.",
        },
        validation={
            "method": "upstream published evaluation",
            "project_validation": "not performed (model not runnable in this deployment)",
        },
        inference_status=inference_status,
        outputs_produced=False,
        metadata={
            "model": MODEL_NAME,
            "reported_status": "blocked",
            "blockers": blockers,
            "reason": "; ".join(blockers) if blockers else "Compatible multi-variable input unavailable.",
            "is_ai_model": True,
            "activation": "Install the official PrithviWxC package, provide MERRA-2 surface/vertical fields and the official climatology scalers, then set PRITHVI_WXC_* environment variables.",
        },
    )


def get_model_registry() -> dict[str, Any]:
    """Return the full model registry with contract and status metadata."""
    return {
        "registry_version": MODEL_REGISTRY_VERSION,
        "models": [_imd_baseline(), _rainfall_hazard(), _prithvi_eo(), _prithvi_wxc()],
        "inference_states": list(INFERENCE_STATES),
        "policy": "Model output is produced only when dependency checks pass; otherwise the model reports its blocker.",
    }


def get_model_catalog() -> dict[str, Any]:
    """Backwards-compatible catalog shape used by the existing API and console."""
    return get_model_registry()