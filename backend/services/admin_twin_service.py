"""Generic administrative-level climate twin adapter.

Uses installed GeoJSON geometries and a validated climate grid. It deliberately
returns ``no_data`` when either geometry or the requested variable is absent.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json

from backend.services.spatial_aggregation_service import aggregate_grid_to_feature

ROOT = Path(__file__).resolve().parents[2]


def _candidate(level: str) -> list[Path]:
    return [
        ROOT / "public" / "data" / "india" / f"india-{level}s.geojson",
        ROOT / "backend" / "data" / "india" / f"india-{level}s.geojson",
    ]


def _features(level: str) -> list[dict[str, Any]]:
    for path in _candidate(level):
        if path.exists():
            with path.open(encoding="utf-8") as handle:
                payload = json.load(handle)
            return payload.get("features", [])
    return []


def build_admin_twin(level: str, admin_id: str, values, latitudes, longitudes, *, variable: str, unit: str, date: str, source: str) -> dict[str, Any]:
    if level not in {"district", "city"}:
        raise ValueError("level must be district or city")
    for feature in _features(level):
        props = feature.get("properties", {})
        identifiers = {str(value) for value in props.values() if value is not None}
        if admin_id in identifiers:
            aggregate = aggregate_grid_to_feature(values, latitudes, longitudes, feature)
            return {
                "status": aggregate["status"],
                "scope": "India",
                "level": level,
                "administrative_id": admin_id,
                "observation_date": date,
                "variable": variable,
                "unit": unit,
                "state_variables": aggregate,
                "provenance": {"source": source, "aggregation": aggregate.get("selection_method")},
            }
    return {
        "status": "no_data",
        "scope": "India",
        "level": level,
        "administrative_id": admin_id,
        "message": f"No validated {level} geometry is installed or the requested administrative ID was not found.",
    }
