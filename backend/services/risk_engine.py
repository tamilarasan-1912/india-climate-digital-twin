"""Deterministic, auditable risk calculations for the climate twin.

This engine deliberately separates component normalization from the final risk
score. It can be replaced by validated hazard-specific models without changing
the API contract.
"""
from __future__ import annotations

from typing import Any, Mapping

from backend.services.risk_contract import build_risk_record


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def combine_components(
    hazard: float | None,
    exposure: float | None,
    vulnerability: float | None,
) -> tuple[float | None, str]:
    """Return a normalized risk score only when all physical components exist."""
    if hazard is None or exposure is None or vulnerability is None:
        return None, "not_available"
    return _bounded(hazard) * _bounded(exposure) * _bounded(vulnerability), "screening_only"


def expected_annual_loss(
    probability: float | None,
    consequence_inr: float | None,
    vulnerability: float | None,
) -> float | None:
    """Compute EAL when all required financial-risk inputs are supplied."""
    if probability is None or consequence_inr is None or vulnerability is None:
        return None
    if probability < 0 or probability > 1:
        raise ValueError("probability must be between 0 and 1")
    if consequence_inr < 0:
        raise ValueError("consequence_inr cannot be negative")
    return probability * consequence_inr * _bounded(vulnerability)


def assess_asset(
    *,
    asset_id: str,
    location_id: str,
    hazard: str,
    hazard_value: float | None,
    exposure_value: float | None,
    vulnerability_value: float | None,
    confidence: float | None,
    assessment_time: str,
    model_version: str,
    hazard_unit: str | None = None,
    data_quality_score: float | None = None,
    validation_status: str = "unvalidated",
    limitations: list[str] | None = None,
    probability: float | None = None,
    consequence_inr: float | None = None,
) -> dict[str, Any]:
    score, status = combine_components(hazard_value, exposure_value, vulnerability_value)
    eal = expected_annual_loss(probability, consequence_inr, vulnerability_value)
    record = build_risk_record(
        asset_id=asset_id,
        location_id=location_id,
        hazard=hazard,
        hazard_value=hazard_value,
        exposure_value=exposure_value,
        vulnerability_value=vulnerability_value,
        risk_score=score,
        confidence=confidence,
        model_version=model_version,
        assessment_time=assessment_time,
        status=status,
        units=hazard_unit,
        data_quality_score=data_quality_score,
        validation_status=validation_status,
        limitations=limitations,
    )
    record["financial"] = {
        "probability": probability,
        "consequence_cost_inr": consequence_inr,
        "expected_annual_loss_inr": eal,
        "status": "calculated" if eal is not None else "not_available",
    }
    return record


def summarize_portfolio(records: list[Mapping[str, Any]]) -> dict[str, Any]:
    scores = [r["risk"]["score"] for r in records if r.get("risk", {}).get("score") is not None]
    eals = [r["financial"]["expected_annual_loss_inr"] for r in records if r.get("financial", {}).get("expected_annual_loss_inr") is not None]
    return {
        "asset_count": len(records),
        "assessed_asset_count": len(scores),
        "risk_score_mean": sum(scores) / len(scores) if scores else None,
        "risk_score_max": max(scores) if scores else None,
        "expected_annual_loss_inr": sum(eals) if eals else None,
        "scientific_status": "screening_only unless every contributing model is validated",
    }
