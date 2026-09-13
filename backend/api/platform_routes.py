"""Industry platform APIs: assets, risk assessments and scenarios."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.models.domain_models import Asset
from backend.services.asset_repository import get_asset, upsert_asset
from backend.services.risk_contract import get_risk_contract
from backend.services.risk_engine import assess_asset
from backend.services.scenario_engine import build_scenario

router = APIRouter(prefix="/api/v1", tags=["industry-platform"])


@router.get("/platform/capabilities")
def capabilities() -> dict[str, Any]:
    return {
        "platform": "Bharat Climate Twin",
        "api_version": "v1",
        "capabilities": {
            "assets": "postgis-backed",
            "risk_contract": get_risk_contract(),
            "scenario_engine": "coupling-aware sensitivity engine",
            "large_data": "external object storage + STAC",
        },
    }


@router.post("/assets")
def create_or_update_asset(asset: Asset) -> dict[str, Any]:
    return upsert_asset(asset)


@router.get("/assets/{asset_id}")
def read_asset(asset_id: str) -> dict[str, Any]:
    result = get_asset(asset_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return result


@router.post("/assets/{asset_id}/risk")
def asset_risk(
    asset_id: str,
    hazard: str,
    hazard_value: float | None = None,
    exposure_value: float | None = None,
    vulnerability_value: float | None = None,
    confidence: float | None = None,
    probability: float | None = None,
    consequence_inr: float | None = None,
    validation_status: str = "unvalidated",
) -> dict[str, Any]:
    asset = get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return assess_asset(
        asset_id=asset_id,
        location_id=asset["location_id"] or asset_id,
        hazard=hazard,
        hazard_value=hazard_value,
        exposure_value=exposure_value,
        vulnerability_value=vulnerability_value,
        confidence=confidence,
        assessment_time=datetime.now(timezone.utc).isoformat(),
        model_version="risk-engine-1.0.0",
        data_quality_score=None,
        validation_status=validation_status,
        limitations=[
            "Generic multiplicative screening engine; hazard-specific physical models must replace it for operational claims."
        ],
        probability=probability,
        consequence_inr=consequence_inr,
    )


@router.post("/scenarios")
def create_scenario(
    scenario_id: str,
    name: str,
    horizon_year: int | None = None,
    climate_scenario: str | None = None,
    precipitation_delta_pct: float = 0,
    temperature_delta_c: float = 0,
    sea_level_rise_m: float = 0,
) -> dict[str, Any]:
    return build_scenario(
        scenario_id=scenario_id,
        name=name,
        horizon_year=horizon_year,
        climate_scenario=climate_scenario,
        precipitation_delta_pct=precipitation_delta_pct,
        temperature_delta_c=temperature_delta_c,
        sea_level_rise_m=sea_level_rise_m,
    )
