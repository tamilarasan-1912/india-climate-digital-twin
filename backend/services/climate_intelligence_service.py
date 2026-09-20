"""Provider-backed climate intelligence retrieval/answering.

This service is deterministic by design: it answers only from project APIs and
never fabricates observations.
"""
from __future__ import annotations
from typing import Any

from backend.services.rainfall_service import get_daily_statistics, get_india_daily_summary
from backend.services.climate_provider_runtime import get_provider_layer

def _summary(layer: str, date: str) -> dict[str, Any]:
    if layer == "rainfall":
        return get_india_daily_summary(date)
    return get_provider_layer(layer, date)

def answer_question(question: str, date: str, layer: str = "rainfall") -> dict[str, Any]:
    q = question.lower().strip()
    if not q:
        raise ValueError("question is required")
    layer = layer.lower().strip()
    supported = {"rainfall", "temperature", "lst", "sst", "anomalies"}
    if layer not in supported:
        raise ValueError(f"unsupported intelligence layer: {layer}")
    data = _summary(layer, date)
    available = bool(data.get("data_available", data.get("status") == "connected"))
    if not available:
        return {
            "answer": f"No validated {layer} data is available for {date}.",
            "status": "NO_DATA",
            "question": question,
            "source": data.get("provider") or "provider_required",
            "date": date,
        }
    if layer == "rainfall":
        avg = data.get("mean_rainfall_mm")
        maximum = data.get("maximum_rainfall_mm")
        answer = f"India rainfall on {date}: mean={avg} mm, maximum={maximum} mm."
    else:
        answer = f"Validated {layer} data is available for {date} from {data.get('provider', 'configured provider')}."
    return {
        "answer": answer,
        "status": "AVAILABLE",
        "question": question,
        "source": data.get("provider", "project provider"),
        "date": date,
        "provenance": data.get("provenance", {}),
    }
