"""State-level climate aggregation for the India Climate Digital Twin.

This service intersects the validated IMD rainfall grid with the repository's
India state boundary dataset. It never substitutes bounding boxes or national
averages for state observations.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import numpy as np
import xarray as xr
from shapely.geometry import Point, shape

from backend.services.climate_risk_service import (
    calculate_risk_score,
    classify_risk_score,
    load_dataset,
)
from backend.services.india_hierarchy_service import STATES_AND_UTS


ROOT = Path(__file__).resolve().parents[2]
BOUNDARY_FILE = ROOT / "public" / "data" / "india" / "india-states.geojson"

STATE_ALIASES = {
    "JAMMU & KASHMIR": "IN-JK",
    "JAMMU AND KASHMIR": "IN-JK",
    "ORISSA": "IN-OR",
    "ODISHA": "IN-OR",
    "UTTARANCHAL": "IN-UK",
    "UTTARAKHAND": "IN-UK",
    "PONDICHERRY": "IN-PY",
    "PUDUCHERRY": "IN-PY",
    "NCT OF DELHI": "IN-DL",
    "DELHI": "IN-DL",
    "TELANGANA": "IN-TG",
    "WEST BENGAL": "IN-WB",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "IN-DH",
}

PROPERTY_KEYS = (
    "id", "ID", "state_id", "STATE_ID", "st_nm", "ST_NM", "state", "STATE",
    "name", "NAME", "NAME_1", "State_Name", "STATE_NAME", "shapeName",
)

_BOUNDARY_CACHE: dict[str, tuple[str, Any]] | None = None
_MASK_CACHE: dict[str, tuple[np.ndarray, np.ndarray]] = {}


def _normalise_name(value: Any) -> str:
    text = re.sub(r"[^A-Z0-9]+", " ", str(value).upper()).strip()
    return re.sub(r"\s+", " ", text)


def _state_id_from_properties(properties: dict[str, Any]) -> str | None:
    for key in PROPERTY_KEYS:
        if key not in properties or properties[key] in (None, ""):
            continue
        value = str(properties[key]).strip().upper()
        if value in {item["id"] for item in STATES_AND_UTS}:
            return value
        normalised = _normalise_name(value)
        if normalised in STATE_ALIASES:
            return STATE_ALIASES[normalised]
        for item in STATES_AND_UTS:
            if normalised == _normalise_name(item["name"]):
                return item["id"]
    return None


def _load_boundaries() -> dict[str, tuple[str, Any]]:
    global _BOUNDARY_CACHE
    if _BOUNDARY_CACHE is not None:
        return _BOUNDARY_CACHE
    if not BOUNDARY_FILE.exists():
        raise FileNotFoundError(f"India state boundary dataset not found: {BOUNDARY_FILE}")
    with BOUNDARY_FILE.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    features = payload.get("features", [])
    if not features:
        raise RuntimeError("India state boundary dataset contains no features")
    result: dict[str, tuple[str, Any]] = {}
    for feature in features:
        state_id = _state_id_from_properties(feature.get("properties", {}))
        geometry = feature.get("geometry")
        if state_id and geometry:
            result[state_id] = (next(item["name"] for item in STATES_AND_UTS if item["id"] == state_id), shape(geometry))
    missing = [item["id"] for item in STATES_AND_UTS if item["id"] not in result]
    if missing:
        raise RuntimeError(f"State boundary dataset is missing administrative geometries: {', '.join(missing)}")
    _BOUNDARY_CACHE = result
    return result


def _dataset_coordinates(dataset: xr.Dataset) -> tuple[np.ndarray, np.ndarray]:
    lat_name = "LATITUDE" if "LATITUDE" in dataset.coords else "latitude"
    lon_name = "LONGITUDE" if "LONGITUDE" in dataset.coords else "longitude"
    if lat_name not in dataset.coords or lon_name not in dataset.coords:
        raise RuntimeError("IMD rainfall dataset does not expose latitude/longitude coordinates")
    return np.asarray(dataset[lat_name].values, dtype=float), np.asarray(dataset[lon_name].values, dtype=float)


def _grid_mask(state_id: str, latitudes: np.ndarray, longitudes: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    cache_key = f"{state_id}:{len(latitudes)}:{len(longitudes)}"
    if cache_key in _MASK_CACHE:
        return _MASK_CACHE[cache_key]
    _, geometry = _load_boundaries()[state_id]
    lat_idx: list[int] = []
    lon_idx: list[int] = []
    for i, latitude in enumerate(latitudes):
        for j, longitude in enumerate(longitudes):
            if geometry.covers(Point(float(longitude), float(latitude))):
                lat_idx.append(i)
                lon_idx.append(j)
    if not lat_idx:
        raise RuntimeError(f"No IMD grid cells intersect state geometry for {state_id}")
    result = np.asarray(lat_idx, dtype=int), np.asarray(lon_idx, dtype=int)
    _MASK_CACHE[cache_key] = result
    return result


def _values_for_state(selected: xr.DataArray, state_id: str, latitudes: np.ndarray, longitudes: np.ndarray) -> np.ndarray:
    lat_idx, lon_idx = _grid_mask(state_id, latitudes, longitudes)
    values = np.asarray(selected.values, dtype=float)
    if values.ndim != 2:
        raise RuntimeError("Expected a 2-D daily rainfall grid")
    return values[lat_idx, lon_idx]


def _stats(values: np.ndarray) -> dict[str, Any]:
    valid = values[np.isfinite(values)]
    if valid.size == 0:
        return {"valid_grid_cells": 0, "mean_rainfall_mm": None, "median_rainfall_mm": None, "maximum_rainfall_mm": None, "mean_hazard_score": None, "risk_category": "no_data"}
    scores = np.asarray([calculate_risk_score(float(value)) for value in valid], dtype=float)
    mean_score = float(np.mean(scores))
    return {
        "valid_grid_cells": int(valid.size),
        "mean_rainfall_mm": round(float(np.mean(valid)), 3),
        "median_rainfall_mm": round(float(np.median(valid)), 3),
        "maximum_rainfall_mm": round(float(np.max(valid)), 3),
        "mean_hazard_score": round(mean_score, 3),
        "maximum_hazard_score": round(float(np.max(scores)), 3),
        "risk_category": classify_risk_score(mean_score),
    }


def get_state_climate_metrics(date: str, state_id: str) -> dict[str, Any]:
    normalized = state_id.strip().upper()
    if normalized not in {item["id"] for item in STATES_AND_UTS}:
        raise ValueError(f"Unknown India state or union territory: {state_id}")
    dataset = load_dataset()
    try:
        time_name = "TIME" if "TIME" in dataset.coords else "time"
        try:
            selected = dataset["RAINFALL"].sel({time_name: date})
        except Exception as error:
            raise ValueError(f"Invalid or unavailable date '{date}'") from error
        latitudes, longitudes = _dataset_coordinates(dataset)
        current = _stats(_values_for_state(selected, normalized, latitudes, longitudes))
        return {
            "status": "available" if current["valid_grid_cells"] else "no_data",
            "scope": "India",
            "level": "state",
            "state_id": normalized,
            "state_name": next(item["name"] for item in STATES_AND_UTS if item["id"] == normalized),
            "observation_date": date,
            "variable": "RAINFALL",
            "units": "mm",
            "metrics": current,
            "data_coverage": {"valid_grid_cells": current["valid_grid_cells"], "selection_method": "IMD 0.25-degree grid cells whose centers are covered by the state polygon"},
            "provenance": {"source": "IMD RF25", "dataset": "RF25_ind2024_rfp25.nc", "aggregation": "spatial mean/median/max over intersecting grid cells"},
        }
    finally:
        dataset.close()


def get_all_state_climate_metrics(date: str) -> dict[str, Any]:
    dataset = load_dataset()
    try:
        time_name = "TIME" if "TIME" in dataset.coords else "time"
        try:
            selected = dataset["RAINFALL"].sel({time_name: date})
        except Exception as error:
            raise ValueError(f"Invalid or unavailable date '{date}'") from error
        latitudes, longitudes = _dataset_coordinates(dataset)
        states = []
        for item in STATES_AND_UTS:
            metrics = _stats(_values_for_state(selected, item["id"], latitudes, longitudes))
            states.append({"state_id": item["id"], "state_name": item["name"], **metrics})
        return {"status": "available", "scope": "India", "level": "state", "observation_date": date, "variable": "RAINFALL", "units": "mm", "count": len(states), "states": states, "aggregation": "IMD 0.25-degree grid cells covered by each state polygon", "source": "IMD RF25"}
    finally:
        dataset.close()


def get_state_twin(date: str, state_id: str) -> dict[str, Any]:
    climate = get_state_climate_metrics(date, state_id)
    metrics = climate["metrics"]
    state_id = climate["state_id"]
    representation = {key: value for key, value in metrics.items() if key not in {"risk_category"}}
    return {"status": climate["status"], "twin": {"scope": "India", "level": "state", "state_id": state_id, "state_name": climate["state_name"], "observation_date": date, "state_variables": representation, "risk": {"mean_hazard_score": metrics["mean_hazard_score"], "maximum_hazard_score": metrics["maximum_hazard_score"], "category": metrics["risk_category"]}, "provenance": climate["provenance"], "aggregation": climate["data_coverage"]}}
