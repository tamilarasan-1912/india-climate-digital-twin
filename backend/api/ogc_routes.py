"""Lightweight OGC-aligned discovery/query endpoints.

These routes implement project-level building blocks inspired by OGC API
Features and STAC. They are not claimed as formal conformance certifications.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

from backend.services.climate_layer_service import get_climate_layer_catalog

router = APIRouter(prefix="/ogc", tags=["ogc"])

ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = ROOT / "data" / "india" / "india-states.geojson"


def _states() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"type": "FeatureCollection", "features": []}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


@router.get("/api")
def ogc_landing() -> dict[str, Any]:
    return {
        "title": "India Climate Digital Twin OGC API building blocks",
        "description": "Discovery and query endpoints for India climate geospatial resources.",
        "conformance": [
            "OGC API - Features concepts",
            "STAC-compatible climate asset metadata",
        ],
        "links": [
            {"rel": "self", "href": "/ogc/api"},
            {"rel": "data", "href": "/ogc/collections"},
        ],
    }


@router.get("/collections")
def collections() -> dict[str, Any]:
    return {
        "collections": [
            {
                "id": "india-states",
                "title": "India states and union territories",
                "itemType": "feature",
                "crs": ["http://www.opengis.net/def/crs/OGC/1.3/CRS84"],
            },
            {
                "id": "climate-layers",
                "title": "India climate layer catalog",
                "itemType": "climate-layer",
                "crs": ["http://www.opengis.net/def/crs/OGC/1.3/CRS84"],
            },
            {
                "id": "extreme-events",
                "title": "Validated climate event observations",
                "itemType": "feature",
                "crs": ["http://www.opengis.net/def/crs/OGC/1.3/CRS84"],
            },
        ]
    }


@router.get("/collections/{collection_id}")
def collection(collection_id: str) -> dict[str, Any]:
    known = {x["id"]: x for x in collections()["collections"]}
    if collection_id not in known:
        return {"status": "not_found", "collection_id": collection_id}
    result = dict(known[collection_id])
    if collection_id == "climate-layers":
        result["layers"] = get_climate_layer_catalog()["layers"]
    return result


@router.get("/collections/india-states/items")
def state_items(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    data = _states()
    features = data.get("features", [])[:limit]
    return {
        "type": "FeatureCollection",
        "features": features,
        "numberMatched": len(data.get("features", [])),
        "numberReturned": len(features),
    }


@router.get("/collections/climate-layers/items")
def climate_layer_items() -> dict[str, Any]:
    layers = get_climate_layer_catalog()["layers"]
    features = [
        {
            "type": "Feature",
            "id": key,
            "geometry": None,
            "properties": {"layer": key, **value},
        }
        for key, value in layers.items()
    ]
    return {"type": "FeatureCollection", "features": features}


@router.get("/collections/extreme-events/items")
def extreme_event_items(date: str | None = Query(default=None)) -> dict[str, Any]:
    # Event records are exposed through the existing validated rainfall event API.
    # This endpoint remains an explicit discovery surface until a persistent
    # event store is connected.
    return {
        "type": "FeatureCollection",
        "features": [],
        "date": date,
        "status": "query_provider_required",
        "source_endpoint": "/api/extreme-events/rainfall/geojson/{date}",
    }


@router.get("/stac")
def stac_catalog() -> dict[str, Any]:
    return {
        "stac_version": "1.1.0",
        "id": "india-climate-digital-twin",
        "type": "Catalog",
        "description": "STAC-compatible catalog boundary for India climate assets.",
        "links": [{"rel": "self", "href": "/ogc/stac"}],
        "collections": [{"id": "climate-layers", "href": "/ogc/collections/climate-layers"}],
        "data_policy": "Large rasters and multidimensional datasets remain in external object storage.",
    }


@router.get("/connected-systems")
def connected_systems() -> dict[str, Any]:
    return {
        "systems": [
            {"id": "imd", "title": "India Meteorological Department", "type": "observation_provider"},
            {"id": "mosdac", "title": "ISRO/MOSDAC", "type": "satellite_provider"},
            {"id": "era5", "title": "ERA5", "type": "reanalysis_provider"},
        ],
        "dynamic_data": "provider adapters are required before live streaming is enabled",
    }
