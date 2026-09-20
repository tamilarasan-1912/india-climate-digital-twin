"""Data and quality endpoints for the India Climate Twin."""
from __future__ import annotations

from fastapi import APIRouter

from backend.services.data_catalog_service import get_data_catalog
from backend.services.data_quality_service import validate_observation

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/catalog")
def data_catalog():
    return get_data_catalog()


@router.post("/validate")
def validate_data(record: dict):
    return validate_observation(record)
