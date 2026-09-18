"""Open administrative-boundary adapter using geoBoundaries open data.

ADM1/ADM2 geometry is fetched lazily and cached in-process. Geometry is never
converted into climate observations; it is only the geographic spine used to
drill from India -> state -> district.
"""
from __future__ import annotations

import json
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from shapely.geometry import shape

BASE = "https://www.geoboundaries.org/api/current/gbOpen/IND"
CACHE_TTL = int(os.getenv("ADMIN_BOUNDARY_CACHE_TTL", "21600"))
CACHE_DIR = Path(__file__).resolve().parents[2] / "backend" / "data" / "admin_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "India-Climate-Digital-Twin/1.0"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _metadata(level: str) -> dict[str, Any]:
    return _fetch_json(f"{BASE}/{level}/")


def _downloaded(level: str) -> dict[str, Any]:
    path = CACHE_DIR / f"IND-{level}.geojson"
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL:
        return json.loads(path.read_text(encoding="utf-8"))
    metadata = _metadata(level)
    url = metadata.get("simplifiedGeometryGeoJSON") or metadata.get("gjDownloadURL")
    if not url:
        raise RuntimeError(f"geoBoundaries returned no GeoJSON URL for {level}")
    data = _fetch_json(url)
    path.write_text(json.dumps(data), encoding="utf-8")
    return data


def _prop(properties: dict[str, Any], *names: str) -> str:
    for name in names:
        value = properties.get(name)
        if value not in (None, ""):
            return str(value)
    return ""


def _state_match(properties: dict[str, Any], state_name: str) -> bool:
    target = state_name.strip().casefold()
    values = {
        _prop(properties, "shapeName", "NAME_1", "state", "STATE", "ADM1_NAME"),
        _prop(properties, "shapeISO", "ADM1_CODE", "GID_1"),
        _prop(properties, "shapeID"),
    }
    return any(v and (v.casefold() == target or target in v.casefold()) for v in values)


@lru_cache(maxsize=1)
def _joined_districts() -> tuple[dict[str, Any], ...]:
    states = _downloaded("ADM1").get("features", [])
    districts = _downloaded("ADM2").get("features", [])
    state_geoms = []
    for feature in states:
        try:
            state_geoms.append((
                _prop(feature.get("properties", {}), "shapeName", "NAME_1", "st_nm", "STATE"),
                shape(feature["geometry"]),
            ))
        except Exception:
            continue

    result = []
    for district in districts:
        try:
            geom = shape(district["geometry"])
            point = geom.representative_point()
            parent = next((name for name, state_geom in state_geoms if state_geom.contains(point)), "")
            props = dict(district.get("properties", {}))
            props["parent_state"] = parent or None
            props["administrative_level"] = "district"
            result.append({"type": "Feature", "geometry": district["geometry"], "properties": props})
        except Exception:
            continue
    return tuple(result)


def get_admin_metadata() -> dict[str, Any]:
    adm1 = _metadata("ADM1")
    adm2 = _metadata("ADM2")
    return {
        "provider": "geoBoundaries",
        "license": "Open Data Commons Open Database License 1.0",
        "attribution_required": True,
        "adm1": {k: adm1.get(k) for k in ("boundaryYearRepresented", "boundaryCanonical", "admUnitCount", "buildDate", "sourceDataUpdateDate")},
        "adm2": {k: adm2.get(k) for k in ("boundaryYearRepresented", "boundaryCanonical", "admUnitCount", "buildDate", "sourceDataUpdateDate")},
        "source": BASE,
    }


def get_districts(state_name: str | None = None) -> dict[str, Any]:
    features = list(_joined_districts())
    if state_name:
        filtered = [f for f in features if _state_match(f["properties"], state_name) or f["properties"].get("parent_state", "").casefold() == state_name.casefold()]
    else:
        filtered = features
    districts = []
    for feature in filtered:
        p = feature["properties"]
        districts.append({
            "id": _prop(p, "shapeID", "shapeISO") or f"district-{len(districts)+1}",
            "name": _prop(p, "shapeName", "NAME_2", "district", "DISTRICT") or "Unnamed district",
            "state": p.get("parent_state"),
            "level": "district",
            "data_status": "geometry_available_climate_metrics_provider_required",
        })
    return {
        "status": "available",
        "count": len(districts),
        "districts": districts,
        "provider": "geoBoundaries",
        "license": "ODbL 1.0",
        "climate_data_status": "District geometry is available; climate metrics require validated spatial aggregation.",
    }


def get_district_geojson(state_name: str | None = None) -> dict[str, Any]:
    features = list(_joined_districts())
    if state_name:
        features = [f for f in features if f["properties"].get("parent_state", "").casefold() == state_name.casefold()]
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {"provider": "geoBoundaries", "license": "ODbL 1.0", "attribution_required": True},
    }
