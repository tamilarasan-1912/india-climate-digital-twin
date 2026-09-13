"""Exposure aggregation for population, infrastructure and economic value.

The engine is intentionally source-driven: it never invents population or
financial values. Missing components remain unavailable and the resulting
composite is labelled as a screening index rather than an observed quantity.
"""
from __future__ import annotations

from typing import Any, Mapping

from backend.models.domain_models import Exposure


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalize(value: float | None, scale: float | None) -> float | None:
    if value is None or scale is None or scale <= 0:
        return None
    return _bounded(value / scale)


def assess_exposure(
    exposure: Exposure,
    *,
    population_scale: float | None = None,
    economic_scale_inr: float | None = None,
) -> dict[str, Any]:
    """Build an auditable exposure assessment from supplied source values."""
    population_index = _normalize(exposure.population, population_scale)
    economic_value = exposure.replacement_value_inr
    economic_index = _normalize(economic_value, economic_scale_inr)
    criticality = exposure.service_criticality
    supply_chain = exposure.supply_chain_dependency

    components = {
        "population": {"value": exposure.population, "index": population_index, "unit": "persons"},
        "infrastructure": {
            "replacement_value_inr": economic_value,
            "index": economic_index,
            "unit": "INR",
        },
        "service_criticality": {"value": criticality, "index": criticality, "unit": "normalized"},
        "supply_chain_dependency": {"value": supply_chain, "index": supply_chain, "unit": "normalized"},
    }

    available = [
        x for x in (population_index, economic_index, criticality, supply_chain)
        if x is not None
    ]
    composite = sum(available) / len(available) if available else None

    return {
        "asset_id": exposure.asset_id,
        "components": components,
        "composite_exposure_index": composite,
        "status": "screening_only" if composite is not None else "not_available",
        "data_quality_score": exposure.data_quality_score,
        "source_ids": exposure.source_ids,
        "limitations": [
            "Normalization scales must be calibrated to the geographic portfolio before operational use.",
            "Population and economic values are source inputs; the engine does not infer missing values.",
        ],
    }


def aggregate_exposures(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize already-assessed exposure records without fabricating missing data."""
    values = [
        float(r["composite_exposure_index"])
        for r in records
        if r.get("composite_exposure_index") is not None
    ]
    population = [
        float(r["components"]["population"]["value"])
        for r in records
        if r.get("components", {}).get("population", {}).get("value") is not None
    ]
    economic = [
        float(r["components"]["infrastructure"]["replacement_value_inr"])
        for r in records
        if r.get("components", {}).get("infrastructure", {}).get("replacement_value_inr") is not None
    ]
    return {
        "asset_count": len(records),
        "assessed_asset_count": len(values),
        "population_exposure": sum(population) if population else None,
        "economic_exposure_inr": sum(economic) if economic else None,
        "mean_exposure_index": sum(values) / len(values) if values else None,
        "status": "screening_only" if values else "not_available",
    }
