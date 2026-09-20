"""Validated district/city hierarchy adapter.

The repository can supply a district/city GeoJSON through the documented data
locations. Until such a dataset is installed, endpoints return explicit
``no_data`` instead of fabricating administrative metrics.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any
import json

ROOT = Path(__file__).resolve().parents[2]
DISTRICT_CANDIDATES = [ROOT / "public/data/india/india-districts.geojson", ROOT / "backend/data/india/india-districts.geojson"]
CITY_CANDIDATES = [ROOT / "public/data/india/india-cities.geojson", ROOT / "backend/data/india/india-cities.geojson"]


def _load(candidates: list[Path], level: str) -> dict[str, Any]:
    for path in candidates:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                payload = json.load(f)
            features = payload.get("features", [])
            return {"status": "available", "level": level, "source": str(path.relative_to(ROOT)), "count": len(features), "features": features}
    return {"status": "no_data", "level": level, "count": 0, "features": [], "required_dataset": f"India {level} boundary GeoJSON"}


def get_districts() -> dict[str, Any]: return _load(DISTRICT_CANDIDATES, "district")
def get_cities() -> dict[str, Any]: return _load(CITY_CANDIDATES, "city")


def resolve_admin(level: str, admin_id: str) -> dict[str, Any]:
    data = get_districts() if level == "district" else get_cities() if level == "city" else {"status": "invalid"}
    if data.get("status") != "available":
        return {"status": "no_data", "level": level, "id": admin_id, "message": "Validated administrative geometry is not installed; no climate metric is fabricated."}
    for feature in data["features"]:
        props = feature.get("properties", {})
        candidates = [str(v) for v in props.values() if v is not None]
        if admin_id in candidates:
            return {"status": "available", "level": level, "id": admin_id, "feature": feature}
    return {"status": "not_found", "level": level, "id": admin_id}
