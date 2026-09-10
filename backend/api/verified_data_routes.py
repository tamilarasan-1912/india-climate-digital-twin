"""Verified authoritative climate-data source endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from backend.services.verified_data_service import get_verified_sources

router = APIRouter(prefix="/api/data", tags=["Verified Data"])


@router.get("/verified-sources")
def verified_sources():
    return get_verified_sources()
