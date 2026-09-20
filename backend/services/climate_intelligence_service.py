"""Provider-backed climate intelligence retrieval and answering.

This service is deterministic by design: every answer is assembled from
project APIs and the connected provider/observation datasets. It never
fabricates observations, forecasts or provenance.

An optional LLM may sit *in front of* this service as an interpretation layer,
but the numeric content of an answer always originates here.
"""
from __future__ import annotations

from typing import Any

from backend.services.climate_layer_service import CLIMATE_LAYERS, get_layer_status
from backend.services.climate_provider import provider_config
from backend.services.climate_provider_runtime import get_provider_layer
from backend.services.climate_risk_service import get_climate_risk_summary
from backend.services.extreme_event_service import get_extreme_event_summary
from backend.services.rainfall_service import get_daily_statistics, get_india_daily_summary
from backend.services.state_twin_service import get_all_state_climate_metrics

SUPPORTED_LAYERS = ("rainfall", "temperature", "lst", "sst", "anomalies")

NO_DATA_MESSAGE = "I do not have validated data for this variable/date/provider."


def _unavailable(layer: str, date: str, question: str, reason: str) -> dict[str, Any]:
    return {
        "answer": f"{NO_DATA_MESSAGE} ({reason})",
        "status": "NO_DATA",
        "data_available": False,
        "question": question,
        "layer": layer,
        "date": date,
        "source": "provider_required",
        "provider_required": True,
    }


def _rainfall_observation(date: str) -> dict[str, Any]:
    # `get_daily_statistics` returns flat keys while `get_india_daily_summary`
    # nests them under "rainfall"; normalise so callers cannot mis-read either.
    summary = get_india_daily_summary(date)
    stats = get_daily_statistics(date)
    nested = summary.get("rainfall", {})
    return {
        "data_available": True,
        "status": "AVAILABLE",
        "provider": "IMD",
        "dataset": "RF25_ind2024_rfp25.nc",
        "variable": "RAINFALL",
        "units": "mm",
        "date": date,
        "mean_rainfall_mm": nested.get("mean_mm", stats["mean"]),
        "maximum_rainfall_mm": nested.get("maximum_mm", stats["maximum"]),
        "minimum_rainfall_mm": nested.get("minimum_mm", stats["minimum"]),
        "median_rainfall_mm": nested.get("median_mm", stats["median"]),
        "grid_points": summary.get("grid_points", stats["grid_points"]),
        "provenance": {
            "source": "IMD",
            "dataset": "RF25_ind2024_rfp25.nc",
            "variable": "RAINFALL",
            "units": "mm",
            "processing": "daily_grid_extraction",
            "status": "validated",
        },
    }


def _summarise_rainfall(date: str, question: str) -> dict[str, Any]:
    data = _rainfall_observation(date)
    answer = (
        f"IMD rainfall for India on {date}: mean {data['mean_rainfall_mm']} mm, "
        f"median {data['median_rainfall_mm']} mm, maximum {data['maximum_rainfall_mm']} mm "
        f"over {data['grid_points']} valid grid points."
    )
    return {**data, "answer": answer, "question": question, "layer": "rainfall"}


def _summarise_state(date: str, question: str, state_id: str) -> dict[str, Any]:
    result = get_all_state_climate_metrics(date)
    state = next((item for item in result["states"] if item["state_id"] == state_id.upper()), None)
    if state is None:
        raise ValueError(f"Unknown India state or union territory: {state_id}")
    if not state["valid_grid_cells"]:
        return {
            "answer": (
                f"No validated rainfall aggregation is available for {state['state_name']} on {date} "
                f"({state.get('status') or 'no_grid_coverage'})."
            ),
            "status": "NO_DATA",
            "data_available": False,
            "question": question,
            "layer": "rainfall",
            "date": date,
            "state_id": state["state_id"],
            "source": "IMD",
        }
    answer = (
        f"{state['state_name']} rainfall on {date}: mean {state['mean_rainfall_mm']} mm, "
        f"maximum {state['maximum_rainfall_mm']} mm over {state['valid_grid_cells']} IMD grid cells. "
        f"Mean hazard score {state['mean_hazard_score']} ({state['risk_category']})."
    )
    return {
        "answer": answer,
        "status": "AVAILABLE",
        "data_available": True,
        "question": question,
        "layer": "rainfall",
        "date": date,
        "state_id": state["state_id"],
        "metrics": state,
        "source": "IMD",
        "provenance": {
            "source": "IMD",
            "dataset": "RF25_ind2024_rfp25.nc",
            "variable": "RAINFALL",
            "units": "mm",
            "processing": "state_polygon_grid_aggregation",
            "status": "validated",
        },
    }


def _summarise_model_status(question: str, date: str) -> dict[str, Any]:
    from backend.services.digital_twin_service import get_model_catalog
    from backend.services.prithvi_wxc_service import get_prithvi_wxc_status

    catalog = get_model_catalog()
    prithvi = get_prithvi_wxc_status()
    names = ", ".join(model["name"] for model in catalog["models"])
    prithvi_status = str(prithvi.get("status", "unknown"))
    blockers = prithvi.get("blockers") or []
    answer = (
        f"Registered models: {names}. Prithvi-WxC status: {prithvi_status}"
        + (f". Blockers: {'; '.join(blockers)}" if blockers else "")
    )
    # When the question is specifically about Prithvi-WxC, the reported status
    # must reflect the model's real availability (e.g. BLOCKED), not merely the
    # fact that the assistant could answer. Reporting AVAILABLE here would tell
    # the UI to show a green light for a model that cannot run.
    if "prithvi" in question.lower():
        return {
            "answer": answer,
            "status": "BLOCKED" if not prithvi.get("inference_ready") else "AVAILABLE",
            "answer_available": True,
            "data_available": bool(prithvi.get("inference_ready")),
            "question": question,
            "date": date,
            "layer": "models",
            "source": "model registry",
            "models": catalog["models"],
            "prithvi_status": prithvi_status,
            "inference_ready": bool(prithvi.get("inference_ready")),
            "blockers": blockers,
        }
    return {
        "answer": answer,
        "status": "AVAILABLE",
        "answer_available": True,
        "data_available": True,
        "question": question,
        "date": date,
        "layer": "models",
        "source": "model registry",
        "models": catalog["models"],
        "prithvi_status": prithvi_status,
        "inference_ready": bool(prithvi.get("inference_ready")),
        "blockers": blockers,
    }


def _summarise_risk(date: str, question: str) -> dict[str, Any]:
    summary = get_climate_risk_summary(date)
    statistics = summary.get("statistics", {})
    return {
        "answer": (
            f"Rainfall-hazard risk for India on {date}: mean score "
            f"{statistics.get('mean_hazard_score')}, maximum score "
            f"{statistics.get('maximum_hazard_score')}. Distribution: "
            f"{summary.get('risk_distribution')}."
        ),
        "status": "AVAILABLE",
        "data_available": True,
        "question": question,
        "date": date,
        "layer": "risk",
        "source": "rainfall hazard engine",
        "risk_model": summary.get("risk_model"),
        "provenance": {
            "source": "IMD",
            "dataset": "RF25_ind2024_rfp25.nc",
            "processing": "rainfall_hazard_scoring",
            "model": summary.get("risk_model"),
            "status": "validated for the rainfall-only hazard model",
        },
    }


def _summarise_events(date: str, question: str) -> dict[str, Any]:
    summary = get_extreme_event_summary(date)
    counts = summary.get("summary", summary)
    answer = (
        f"Extreme rainfall points detected on {date}: "
        f"{counts.get('total_extreme_points', 0)} total "
        f"(heavy {counts.get('heavy_points', 0)}, very heavy "
        f"{counts.get('very_heavy_points', 0)}, extremely heavy "
        f"{counts.get('extremely_heavy_points', 0)})."
    )
    result: dict[str, Any] = {
        "answer": answer,
        "status": "AVAILABLE",
        "data_available": True,
        "question": question,
        "date": date,
        "layer": "events",
        "source": "IMD-derived event detector",
        "thresholds": summary.get("thresholds"),
        "summary": counts,
    }
    # "Which states ..." needs an actual geographic breakdown. Ranking by the
    # maximum observed state rainfall answers it from validated IMD values
    # instead of the national count alone.
    if "which state" in question.lower() or "states had" in question.lower():
        heavy_mm = (summary.get("thresholds") or {}).get("heavy_mm")
        if heavy_mm is not None:
            states = get_all_state_climate_metrics(date)["states"]
            ranked = sorted(
                (s for s in states if (s.get("maximum_rainfall_mm") or 0) >= heavy_mm),
                key=lambda s: s["maximum_rainfall_mm"],
                reverse=True,
            )
            names = ", ".join(
                f"{s['state_name']} ({s['maximum_rainfall_mm']} mm)" for s in ranked
            )
            result["affected_states"] = [
                {
                    "state_id": s["state_id"],
                    "state_name": s["state_name"],
                    "maximum_rainfall_mm": s["maximum_rainfall_mm"],
                    "mean_rainfall_mm": s["mean_rainfall_mm"],
                    "valid_grid_cells": s["valid_grid_cells"],
                }
                for s in ranked
            ]
            result["threshold_used_mm"] = heavy_mm
            result["answer"] = (
                f"{answer} States containing at least one grid point at or above the "
                f"{heavy_mm} mm heavy-rain threshold: {names or 'none'}."
            )
    return result


def _summarise_layer(layer: str, date: str, question: str) -> dict[str, Any]:
    payload = get_provider_layer(layer, date)
    if payload.get("status") == "NO_DATA" or not payload.get("data_available"):
        config = provider_config(layer)
        return _unavailable(
            layer,
            date,
            question,
            f"{config['env_var']} is not connected"
            if config.get("env_var")
            else "no validated provider adapter is connected",
        )
    answer = (
        f"Validated {layer} data is available for {date} from "
        f"{payload.get('provider', 'configured provider')}."
    )
    return {
        "answer": answer,
        "status": "AVAILABLE",
        "data_available": True,
        "question": question,
        "layer": layer,
        "date": date,
        "source": payload.get("provider"),
        "provenance": payload.get("provenance", {}),
    }


def _states_mentioned(question: str) -> list[str]:
    from backend.services.india_hierarchy_service import STATES_AND_UTS

    matches = []
    for item in STATES_AND_UTS:
        if item["name"].lower() in question or item["id"].lower() in question:
            matches.append(item["id"])
    return matches


VARIABLE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("anomalies", ("anomaly", "anomalies")),
    ("temperature", ("temperature", "temp ")),
    ("lst", ("land surface temperature", "lst")),
    ("sst", ("sea surface temperature", "sst")),
    ("rainfall", ("rainfall", "rain", "precipitation")),
)


def _variable_mentioned(question: str) -> str | None:
    """Resolve the climate variable a question is actually asking about."""
    for layer, keywords in VARIABLE_KEYWORDS:
        if any(keyword in question for keyword in keywords):
            return layer
    return None


def _summarise_provenance(date: str, question: str) -> dict[str, Any]:
    """Explain where the connected observation for this date came from."""
    data = _rainfall_observation(date)
    provenance = data["provenance"]
    answer = (
        f"The connected observation for {date} is {provenance['variable']} from "
        f"{provenance['source']} dataset {provenance['dataset']}, processed by "
        f"{provenance['processing']} (validation status: {provenance['status']})."
    )
    return {
        **data,
        "answer": answer,
        "question": question,
        "layer": "provenance",
        "source": provenance["source"],
    }


def answer_question(question: str, date: str, layer: str = "rainfall") -> dict[str, Any]:
    """Answer a climate question strictly from connected project data."""
    q = question.lower().strip()
    if not q:
        raise ValueError("question is required")
    key = layer.lower().strip()
    if key not in SUPPORTED_LAYERS and key not in {"risk", "events", "models"}:
        raise ValueError(f"unsupported intelligence layer: {layer}")

    if "prithvi" in q or "forecast model" in q or "which model" in q:
        return _summarise_model_status(question, date)
    if "provenance" in q or "data source" in q or "where did" in q or "come from" in q:
        return _summarise_provenance(date, question)
    if "extreme" in q or "event" in q:
        return _summarise_events(date, question)
    # A question naming a specific variable must be answered for that variable,
    # not for the caller's default layer.
    requested = _variable_mentioned(q)
    if requested and requested != key:
        return _summarise_layer(requested, date, question)
    for state_id in _states_mentioned(q):
        return _summarise_state(date, question, state_id)
    if key == "rainfall" and "risk" in q:
        return _summarise_risk(date, question)
    if key == "rainfall":
        return _summarise_rainfall(date, question)
    if key == "risk":
        return _summarise_risk(date, question)
    if key == "events":
        return _summarise_events(date, question)
    if key == "models":
        return _summarise_model_status(question, date)
    return _summarise_layer(key, date, question)


def get_intelligence_capabilities() -> dict[str, Any]:
    """Describe what the assistant can answer and from which source."""
    return {
        "deterministic": True,
        "llm_is_interpretation_layer_only": True,
        "supported_layers": list(SUPPORTED_LAYERS),
        "supported_intents": [
            "national rainfall observation",
            "state-level rainfall aggregation",
            "rainfall-hazard risk summary",
            "extreme rainfall events",
            "provider-backed temperature/LST/SST/anomaly lookup",
            "model and Prithvi-WxC status",
        ],
        "layer_status": {key: get_layer_status(key, "1970-01-01")["status"] for key in CLIMATE_LAYERS},
        "no_data_message": NO_DATA_MESSAGE,
    }