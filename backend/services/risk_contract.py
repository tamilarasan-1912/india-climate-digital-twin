"""Common risk contract for the India Climate Digital Twin.

The contract is intentionally model-agnostic. It standardizes the information
that every future hazard/asset risk engine must return without pretending that
an unimplemented physical model exists.
"""

from __future__ import annotations

from typing import Any, Mapping

RISK_CONTRACT_VERSION = "1.0.0"

HAZARDS = (
    "flood",
    "heat",
    "drought",
    "cyclone",
    "landslide",
    "wildfire",
    "air_quality",
    "coastal_inundation",
)

RISK_COMPONENTS = ("hazard", "exposure", "vulnerability")


def build_risk_record(
    *,
    asset_id: str,
    location_id: str,
    hazard: str,
    hazard_value: float | None,
    exposure_value: float | None,
    vulnerability_value: float | None,
    risk_score: float | None,
    confidence: float | None,
    model_version: str,
    assessment_time: str,
    status: str,
    units: str | None = None,
    data_quality_score: float | None = None,
    validation_status: str = "unvalidated",
    limitations: list[str] | None = None,
) -> dict[str, Any]:
    """Create a traceable asset-risk record.

    ``status`` should distinguish values such as ``screening_only``,
    ``validated`` and ``not_available``. A missing physical model must never be
    represented as a zero-risk value.
    """
    if hazard not in HAZARDS:
        raise ValueError(f"Unsupported hazard '{hazard}'. Expected one of {HAZARDS}.")
    if not asset_id or not location_id:
        raise ValueError("asset_id and location_id are required")
    if confidence is not None and not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    if data_quality_score is not None and not 0 <= data_quality_score <= 1:
        raise ValueError("data_quality_score must be between 0 and 1")
    if risk_score is not None and not 0 <= risk_score <= 1:
        raise ValueError("risk_score must be normalized to 0..1")

    return {
        "contract_version": RISK_CONTRACT_VERSION,
        "asset_id": asset_id,
        "location_id": location_id,
        "assessment_time": assessment_time,
        "hazard": {
            "type": hazard,
            "value": hazard_value,
            "unit": units,
        },
        "exposure": {
            "value": exposure_value,
        },
        "vulnerability": {
            "value": vulnerability_value,
        },
        "risk": {
            "score": risk_score,
            "formula": "hazard × exposure × vulnerability",
        },
        "confidence": confidence,
        "data_quality_score": data_quality_score,
        "model_version": model_version,
        "validation_status": validation_status,
        "status": status,
        "limitations": list(limitations or []),
        "integrity": {
            "missing_components_are_explicit": True,
            "zero_is_not_used_for_missing_data": True,
            "uncertainty_required_for_operational_prediction": True,
        },
    }


def validate_risk_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the minimum structural requirements of a risk record."""
    required = ("contract_version", "asset_id", "location_id", "assessment_time", "hazard", "risk", "model_version", "status")
    missing = [key for key in required if key not in record]
    if missing:
        raise ValueError("Risk record is missing required fields: " + ", ".join(missing))
    if record["contract_version"] != RISK_CONTRACT_VERSION:
        raise ValueError("Unsupported risk contract version")
    hazard = record["hazard"]
    if not isinstance(hazard, Mapping) or hazard.get("type") not in HAZARDS:
        raise ValueError("Risk record contains an invalid hazard type")
    return {"valid": True, "contract_version": RISK_CONTRACT_VERSION}


def get_risk_contract() -> dict[str, Any]:
    return {
        "version": RISK_CONTRACT_VERSION,
        "hazards": list(HAZARDS),
        "components": list(RISK_COMPONENTS),
        "formula": "Risk = Hazard × Exposure × Vulnerability",
        "financial_formula": "Expected Annual Loss = probability × exposure × vulnerability function × consequence cost",
        "required_metadata": [
            "assessment_time",
            "model_version",
            "validation_status",
            "confidence",
            "data_quality_score",
            "limitations",
        ],
    }
