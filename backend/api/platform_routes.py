"""Industry platform APIs: assets, exposure, risk, heat, scenarios, datasets and alerts."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Depends, Request

from backend.models.domain_models import Asset, Exposure
from backend.services.alert_service import build_alert, get_language_catalog
from backend.services.asset_repository import get_asset, upsert_asset
from backend.services.auth_service import operator_auth_status, require_operator
from backend.services.dataset_catalog import get_catalog_contract
from backend.services.dataset_catalog_store import (
    catalog_summary,
    delete_dataset,
    get_dataset,
    register_connected_datasets,
    register_dataset,
    search_datasets,
)
from backend.services.exposure_engine import assess_exposure
from backend.services.flood_twin_service import get_flood_twin_status
from backend.services.heat_risk_engine import assess_heat_risk
from backend.services.risk_contract import get_risk_contract
from backend.services.risk_engine import assess_asset
from backend.services.scenario_engine import build_scenario
from backend.services.multilingual_alert_service import render_alert

router = APIRouter(prefix="/api/v1", tags=["industry-platform"])


@router.get("/platform/capabilities")
def capabilities() -> dict[str, Any]:
    return {
        "platform": "Bharat Climate Twin",
        "api_version": "v1",
        "capabilities": {
            "assets": "postgis-backed",
            "exposure": "source-driven population/infrastructure/economic screening",
            "heat": "temperature-humidity-exposure screening",
            "risk_contract": get_risk_contract(),
            "scenario_engine": "coupling-aware sensitivity engine",
            "dataset_catalog": "STAC-compatible",
            "alerts": "channel-neutral multilingual payloads",
            "flood_twin": get_flood_twin_status(),
            "large_data": "external object storage + STAC",
        },
    }


@router.get("/catalog/contract")
def catalog_contract() -> dict[str, Any]:
    return get_catalog_contract()


@router.get("/catalog/summary")
def dataset_catalog_summary() -> dict[str, Any]:
    return catalog_summary()


@router.get("/catalog/datasets")
def dataset_catalog_search(
    provider: str | None = None,
    variable: str | None = None,
    text: str | None = None,
    validation_status: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    results = search_datasets(
        provider=provider,
        variable=variable,
        text=text,
        validation_status=validation_status,
        limit=limit,
    )
    return {"count": len(results), "datasets": results, **catalog_summary()}


@router.get("/catalog/datasets/{dataset_id}")
def dataset_catalog_read(dataset_id: str) -> dict[str, Any]:
    record = get_dataset(dataset_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return record


@router.post("/catalog/datasets")
def dataset_catalog_register(record: dict[str, Any], request: Request) -> dict[str, Any]:
    require_operator(request)
    return register_dataset(record)


@router.delete("/catalog/datasets/{dataset_id}")
def dataset_catalog_delete(dataset_id: str, request: Request) -> dict[str, Any]:
    require_operator(request)
    if not delete_dataset(dataset_id):
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"status": "deleted", "dataset_id": dataset_id}


@router.post("/catalog/register-connected")
def dataset_catalog_register_connected(request: Request) -> dict[str, Any]:
    require_operator(request)
    return register_connected_datasets()


@router.get("/security/status")
def security_status() -> dict[str, Any]:
    return {
        "cors_allowed_origins": [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()],
        "rate_limit_per_minute": int(os.getenv("RATE_LIMIT_PER_MINUTE", "240")),
        "trust_proxy_headers": os.getenv("TRUST_PROXY_HEADERS", "false"),
        **operator_auth_status(),
    }


@router.get("/flood/status")
def flood_status() -> dict[str, Any]:
    return get_flood_twin_status()


@router.get("/alerts/languages")
def alert_languages() -> list[dict[str, str]]:
    return get_language_catalog()


@router.post("/alerts/preview")
def alert_preview(hazard: str, severity: str, region: str, condition: str, action: str, expires: str, language: str = "en") -> dict[str, Any]:
    return build_alert(hazard=hazard, severity=severity, region=region, condition=condition, action=action, expires=expires, language=language)


@router.post("/assets")
def create_or_update_asset(asset: Asset, request: Request) -> dict[str, Any]:
    require_operator(request)
    return upsert_asset(asset)


@router.get("/assets/{asset_id}")
def read_asset(asset_id: str) -> dict[str, Any]:
    result = get_asset(asset_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return result


@router.post("/assets/{asset_id}/exposure")
def asset_exposure(
    asset_id: str,
    population: float | None = None,
    replacement_value_inr: float | None = None,
    annual_revenue_inr: float | None = None,
    service_criticality: float | None = None,
    supply_chain_dependency: float | None = None,
    data_quality_score: float | None = None,
    population_scale: float | None = None,
    economic_scale_inr: float | None = None,
    source_ids: list[str] | None = None,
) -> dict[str, Any]:
    asset = get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    exposure = Exposure(
        asset_id=asset_id,
        population=population,
        replacement_value_inr=replacement_value_inr,
        annual_revenue_inr=annual_revenue_inr,
        service_criticality=service_criticality,
        supply_chain_dependency=supply_chain_dependency,
        data_quality_score=data_quality_score,
        source_ids=source_ids or [],
    )
    return assess_exposure(exposure, population_scale=population_scale, economic_scale_inr=economic_scale_inr)


@router.post("/hazards/heat")
def heat_hazard(
    temperature_c: float,
    relative_humidity_pct: float,
    exposure_index: float | None = None,
    confidence: float | None = None,
) -> dict[str, Any]:
    return assess_heat_risk(
        temperature_c=temperature_c,
        relative_humidity_pct=relative_humidity_pct,
        exposure_index=exposure_index,
        confidence=confidence,
    )


@router.post("/assets/{asset_id}/risk")
def asset_risk(asset_id: str, hazard: str, hazard_value: float | None = None, exposure_value: float | None = None, vulnerability_value: float | None = None, confidence: float | None = None, probability: float | None = None, consequence_inr: float | None = None, validation_status: str = "unvalidated") -> dict[str, Any]:
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
        validation_status=validation_status,
        limitations=["Generic multiplicative screening engine; validated hazard-specific models are required for operational claims."],
        probability=probability,
        consequence_inr=consequence_inr,
    )


@router.post("/scenarios")
def create_scenario(scenario_id: str, name: str, horizon_year: int | None = None, climate_scenario: str | None = None, precipitation_delta_pct: float = 0, temperature_delta_c: float = 0, sea_level_rise_m: float = 0) -> dict[str, Any]:
    return build_scenario(scenario_id=scenario_id, name=name, horizon_year=horizon_year, climate_scenario=climate_scenario, precipitation_delta_pct=precipitation_delta_pct, temperature_delta_c=temperature_delta_c, sea_level_rise_m=sea_level_rise_m)
