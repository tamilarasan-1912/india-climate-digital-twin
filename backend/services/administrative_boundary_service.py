"""Open administrative-boundary adapter using geoBoundaries open data.

ADM1/ADM2 geometry is fetched lazily and cached in-process. Geometry is never
converted into climate observations; it is only the geographic spine used to
drill from India -> state -> district.
"""
from __future__ import annotations

import json
import logging
import os
import time
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from shapely.geometry import shape

from backend.services.admin_names import normalise_admin_name

logger = logging.getLogger(__name__)

BASE = "https://www.geoboundaries.org/api/current/gbOpen/IND"
CACHE_TTL = int(os.getenv("ADMIN_BOUNDARY_CACHE_TTL", "21600"))
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[2] / "backend" / "data" / "admin_cache"
# Deployments may mount a validated cache outside the application image. The
# default remains the repository runtime-cache location and is never populated
# with synthetic geometry.
CACHE_DIR = Path(os.getenv("ADMIN_BOUNDARY_CACHE_DIR") or DEFAULT_CACHE_DIR)


def _fetch_json(url: str) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "India-Climate-Digital-Twin/1.0"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _metadata(level: str) -> dict[str, Any]:
    payload = _fetch_json(f"{BASE}/{level}/")
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"geoBoundaries metadata for {level} was not a JSON object"
        )
    return payload


def _cache_path(level: str) -> Path:
    """Resolve the cache file for a level, creating the directory on demand.

    The directory is not created at import time, so importing this module has
    no filesystem side effects.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"IND-{level}.geojson"


def _read_cache(level: str) -> dict[str, Any] | None:
    """Return the on-disk payload for a level, or None if unusable."""
    path = _cache_path(level)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("discarding unreadable boundary cache for %s", level)
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        logger.warning("discarding malformed boundary cache for %s", level)
        return None
    return payload


def get_boundary_cache_status() -> dict[str, Any]:
    """Report local geometry availability without triggering provider I/O.

    This is used by health/status endpoints, where a missing cache should be
    reported quickly as a dependency gap rather than causing a 30-second
    upstream request. The request path still lazily refreshes stale/missing
    files through geoBoundaries.
    """
    present: dict[str, bool] = {}
    valid: dict[str, bool] = {}
    for level in ("ADM1", "ADM2"):
        path = CACHE_DIR / f"IND-{level}.geojson"
        present[level] = path.exists()
        if not present[level]:
            valid[level] = False
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            valid[level] = isinstance(payload, dict) and isinstance(payload.get("features"), list)
        except (OSError, ValueError):
            valid[level] = False
    available = all(valid.values())
    return {
        "state": "AVAILABLE" if available else "PROVIDER REQUIRED",
        "cache_present": present,
        "cache_valid": valid,
        "provider": "geoBoundaries",
        "levels": ["ADM1", "ADM2"],
        "note": (
            "Real cached ADM1/ADM2 geometry is available."
            if available
            else "Mount or fetch validated geoBoundaries ADM1/ADM2 geometry; no synthetic boundaries are used."
        ),
    }


def _download(level: str) -> dict[str, Any]:

    metadata = _metadata(level)
    url = metadata.get("simplifiedGeometryGeoJSON") or metadata.get("gjDownloadURL")
    if not url:
        raise RuntimeError(f"geoBoundaries returned no GeoJSON URL for {level}")
    payload = _fetch_json(url)
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise RuntimeError(
            f"geoBoundaries geometry for {level} was not a FeatureCollection"
        )
    _cache_path(level).write_text(json.dumps(payload), encoding="utf-8")
    return payload


@lru_cache(maxsize=8)
def _downloaded(level: str) -> dict[str, Any]:
    """Return boundary geometry for a level, degrading gracefully when offline.

    Resolution order:
    1. A cache file within ``CACHE_TTL`` is trusted as-is.
    2. Otherwise the provider is contacted and a good response is cached.
    3. If the provider is unreachable but a cache file exists, the last
       known-good geometry is used with a warning rather than failing.

    Nothing is ever synthesised: every return value is geometry parsed from the
    provider or from a file already on disk. When neither is available the
    caller gets ``RuntimeError``, which the API maps to 503 "provider
    unavailable" rather than a client error.
    """
    path = _cache_path(level)
    if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL:
        cached = _read_cache(level)
        if cached is not None:
            return cached

    try:
        return _download(level)
    except (OSError, RuntimeError) as error:
        stale = _read_cache(level)
        if stale is not None:
            logger.warning(
                "geoBoundaries %s unavailable (%s); serving cached geometry", level, error
            )
            return stale
        raise RuntimeError(
            f"administrative boundary geometry for {level} is unavailable: {error}"
        ) from error


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
            # Assign by largest shared area rather than by a single
            # representative point: ADM1/ADM2 boundaries are digitised
            # separately, so an island district such as Lakshadweep has a
            # representative point that falls outside its own state polygon
            # even though the two geometries clearly intersect.
            best_name = ""
            best_area = 0.0
            for name, state_geom in state_geoms:
                if not state_geom.intersects(geom):
                    continue
                area = state_geom.intersection(geom).area
                if area > best_area:
                    best_name, best_area = name, area
            props = dict(district.get("properties", {}))
            props["parent_state"] = best_name or None
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


def _parent_state(properties: dict[str, Any]) -> str:
    """Return the district's parent state name, tolerating a missing join.

    ``parent_state`` is ``None`` for the occasional district whose state polygon
    could not be resolved (Lakshadweep in the current geoBoundaries release), so
    callers must not assume a string.
    """
    value = properties.get("parent_state")
    return str(value) if value else ""


def _resolve_state_name(state_name: str) -> str:
    """Accept either a state name or a hierarchy state ID (e.g. ``IN-TN``)."""
    from backend.services.india_hierarchy_service import STATES_AND_UTS

    target = state_name.strip().upper()
    for item in STATES_AND_UTS:
        if item["id"] == target:
            return item["name"]
    return state_name


def _parent_state_matches(properties: dict[str, Any], state_name: str) -> bool:
    """Compare parent state names after diacritic folding.

    geoBoundaries spells some states with diacritics ("Tamil Nādu",
    "Mahārāshtra"), so a raw case-folded comparison drops every district of
    those states from the map.
    """
    parent = _parent_state(properties)
    if not parent:
        return False
    return normalise_admin_name(parent) == normalise_admin_name(_resolve_state_name(state_name))


def get_districts(state_name: str | None = None) -> dict[str, Any]:
    features = list(_joined_districts())
    if state_name:
        filtered = [f for f in features if _state_match(f["properties"], state_name) or _parent_state_matches(f["properties"], state_name)]
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
            "geometry_status": "available",
            "climate_metrics_endpoint": f"/api/india/district/{_prop(p, 'shapeID', 'shapeISO')}/climate/{{date}}",
        })
    return {
        "status": "available",
        "count": len(districts),
        "districts": districts,
        "provider": "geoBoundaries",
        "license": "ODbL 1.0",
        "climate_data_status": "Geometry from geoBoundaries ADM2. District rainfall metrics are served by "
        "/api/india/district/{district_id}/climate/{date} and /api/india/state/{state_id}/districts/climate/{date}.",
    }


def list_district_geometries() -> list[dict[str, Any]]:
    """Return district geometry with stable identifiers for spatial aggregation.

    Each item exposes ``id``, ``name``, ``state`` and the parsed Shapely
    ``geometry`` so climate services can intersect real observations with real
    polygons without re-parsing the source GeoJSON.
    """
    result: list[dict[str, Any]] = []
    for feature in _joined_districts():
        geometry = shape(feature["geometry"])
        props = feature["properties"]
        result.append({
            "id": _prop(props, "shapeID", "shapeISO") or f"district-{len(result) + 1}",
            "name": _prop(props, "shapeName", "NAME_2", "district", "DISTRICT") or "Unnamed district",
            "state": props.get("parent_state"),
            "level": "district",
            "geometry": geometry,
        })
    return result


def get_district_geojson(state_name: str | None = None) -> dict[str, Any]:
    features = list(_joined_districts())
    if state_name:
        features = [f for f in features if _parent_state_matches(f["properties"], state_name)]
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {"provider": "geoBoundaries", "license": "ODbL 1.0", "attribution_required": True},
    }
