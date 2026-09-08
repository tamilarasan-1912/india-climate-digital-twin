"""Prithvi-WxC contract and inference readiness routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.services.merra2_contract_service import build_contract_report
from backend.services.forecast_readiness_service import assess_prithvi_readiness
from backend.services.prithvi_wxc_service import run_local_inference

router = APIRouter(prefix="/api/forecast/prithvi-wxc", tags=["Prithvi-WxC"])


@router.get("/contract")
def contract():
    return build_contract_report()


@router.get("/readiness")
def readiness():
    report = build_contract_report()
    return {
        "contract": report,
        "readiness": assess_prithvi_readiness({
            "valid": report["status"] == "ready",
            "variables": report["variables"]["common"],
        }),
    }


@router.post("/infer")
def infer():
    try:
        return run_local_inference()
    except (RuntimeError, FileNotFoundError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
