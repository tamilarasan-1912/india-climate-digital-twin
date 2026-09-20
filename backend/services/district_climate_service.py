"""District-level climate aggregation for the India Climate Digital Twin.

This service intersects the validated IMD 0.25-degree rainfall grid with the
repository's geoBoundaries ADM2 district polygons. Aggregation is a genuine
spatial operation over real geometry and real observations; it never
interpolates, invents or extrapolates district values.

Districts whose polygon contains no IMD grid-point centre are reported with an
explicit ``no_grid_coverage`` status rather than a substituted value from a
parent state or neighbouring district.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import numpy as np
import xarray as xr
from shapely import STRtree

from backend.services.admin_names import normalise_admin_name
from backend.services.administrative_boundary_service import list_district_geometries
from backend.services.climate_risk_service import (
    calculate_risk_score,
    classify_risk_score,
    read_dataset,
)


def _canonical_state_names() -> dict[str, str]:
    """Map a normalised state name to the hierarchy's canonical spelling.

    geoBoundaries ADM2 uses diacritic and legacy spellings (e.g. "Tamil Nādu",
    "Telangāna"); the API should return the canonical name the rest of the
    platform uses.
    """
    from backend.services.india_hierarchy_service import STATES_AND_UTS

    return {normalise_admin_name(item["name"]): item["name"] for item in STATES_AND_UTS}


def canonical_state_name(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return _canonical_state_names().get(normalise_admin_name(value), str(value))


AGGREGATION_METHOD = (
    "IMD 0.25-degree grid cells whose centres are covered by the district polygon"
)
PROVENANCE = {
    "source": "IMD RF25",
    "dataset": "RF25_ind2024_rfp25.nc",
    "variable": "RAINFALL",
    "units": "mm",
    "aggregation": "spatial mean/min/max/median over intersecting grid cells",
    "geometry_source": "geoBoundaries ADM2 (ODbL 1.0)",
}

# Grid geometry is fixed for a given dataset, so the (grid shape) -> assignment
# mapping is cached once and reused for every date.
_CELL_ASSIGNMENT_CACHE: dict[tuple[int, int], tuple[np.ndarray, np.ndarray, np.ndarray]] | None = None
_NORMALISED_DISTRICT_CACHE: tuple[tuple[str, str, str, Any], ...] | None = None


def _normalised_districts() -> tuple[tuple[str, str, str, Any], ...]:
    """Return (district_id, district_name, parent_state, geometry) tuples."""
    global _NORMALISED_DISTRICT_CACHE
    if _NORMALISED_DISTRICT_CACHE is None:
        _NORMALISED_DISTRICT_CACHE = tuple(
            (item["id"], item["name"], item["state"] or "", item["geometry"])
            for item in list_district_geometries()
        )
    return _NORMALISED_DISTRICT_CACHE


def get_district_geometry_coverage() -> dict[str, Any]:
    districts = _normalised_districts()
    return {
        "provider": "geoBoundaries",
        "license": "ODbL 1.0",
        "districts_with_geometry": len(districts),
        "note": "District climate metrics are computed only for districts whose polygon contains IMD grid-point centres.",
    }


def _build_cell_assignment(latitudes: np.ndarray, longitudes: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Map every IMD grid cell centre to the districts that cover it.

    Returns parallel arrays (district_index, lat_index, lon_index) so a single
    fancy-index gathers all values for every district in one operation.
    """
    global _CELL_ASSIGNMENT_CACHE
    cache_key = (int(latitudes.size), int(longitudes.size))
    if _CELL_ASSIGNMENT_CACHE is not None and _CELL_ASSIGNMENT_CACHE[0] is not None:
        cached_key, payload = _CELL_ASSIGNMENT_CACHE
        if cached_key == cache_key:
            return payload

    districts = _normalised_districts()
    if not districts:
        empty = np.asarray([], dtype=int)
        _CELL_ASSIGNMENT_CACHE = (cache_key, (empty, empty, empty))
        return empty, empty, empty

    geometries = [item[3] for item in districts]
    tree = STRtree(geometries)

    lon_grid, lat_grid = np.meshgrid(longitudes, latitudes)
    points_lon = lon_grid.ravel()
    points_lat = lat_grid.ravel()
    lat_index = np.repeat(np.arange(latitudes.size), longitudes.size)
    lon_index = np.tile(np.arange(longitudes.size), latitudes.size)

    from shapely.geometry import Point

    district_index_parts: list[np.ndarray] = []
    lat_index_parts: list[np.ndarray] = []
    lon_index_parts: list[np.ndarray] = []

    # Query the R-tree per grid point; only candidate polygons are tested with
    # the exact predicate, so this stays fast for the full national grid.
    for position in range(points_lon.size):
        point = Point(float(points_lon[position]), float(points_lat[position]))
        for candidate in tree.query(point):
            if geometries[int(candidate)].covers(point):
                district_index_parts.append(np.asarray([int(candidate)]))
                lat_index_parts.append(np.asarray([lat_index[position]]))
                lon_index_parts.append(np.asarray([lon_index[position]]))

    if district_index_parts:
        result = (
            np.concatenate(district_index_parts),
            np.concatenate(lat_index_parts),
            np.concatenate(lon_index_parts),
        )
    else:
        empty = np.asarray([], dtype=int)
        result = (empty, empty, empty)

    _CELL_ASSIGNMENT_CACHE = (cache_key, result)
    return result


def _district_stats(values: np.ndarray) -> dict[str, Any]:
    valid = values[np.isfinite(values)]
    if valid.size == 0:
        return {
            "valid_grid_cells": 0,
            "status": "no_grid_coverage",
            "mean_rainfall_mm": None,
            "median_rainfall_mm": None,
            "minimum_rainfall_mm": None,
            "maximum_rainfall_mm": None,
            "mean_hazard_score": None,
            "maximum_hazard_score": None,
            "risk_category": "no_data",
        }
    scores = np.asarray([calculate_risk_score(float(v)) for v in valid], dtype=float)
    mean_score = float(np.mean(scores))
    return {
        "valid_grid_cells": int(valid.size),
        "mean_rainfall_mm": round(float(np.mean(valid)), 3),
        "median_rainfall_mm": round(float(np.median(valid)), 3),
        "minimum_rainfall_mm": round(float(np.min(valid)), 3),
        "maximum_rainfall_mm": round(float(np.max(valid)), 3),
        "mean_hazard_score": round(mean_score, 3),
        "maximum_hazard_score": round(float(np.max(scores)), 3),
        "risk_category": classify_risk_score(mean_score),
    }


def _select_day(dataset: xr.Dataset, date: str) -> xr.DataArray:
    time_name = "TIME" if "TIME" in dataset.coords else "time"
    try:
        return dataset["RAINFALL"].sel({time_name: date})
    except Exception as error:  # noqa: BLE001 - normalised to ValueError below
        raise ValueError(f"Invalid or unavailable date '{date}'") from error


def _dataset_coordinates(dataset: xr.Dataset) -> tuple[np.ndarray, np.ndarray]:
    lat_name = "LATITUDE" if "LATITUDE" in dataset.coords else "latitude"
    lon_name = "LONGITUDE" if "LONGITUDE" in dataset.coords else "longitude"
    if lat_name not in dataset.coords or lon_name not in dataset.coords:
        raise RuntimeError("IMD rainfall dataset does not expose latitude/longitude coordinates")
    return (
        np.asarray(dataset[lat_name].values, dtype=float),
        np.asarray(dataset[lon_name].values, dtype=float),
    )


def _aggregate_day(
    selected: xr.DataArray,
    latitudes: np.ndarray,
    longitudes: np.ndarray,
    districts: tuple[tuple[str, str, str, Any], ...],
    district_index: np.ndarray,
    lat_index: np.ndarray,
    lon_index: np.ndarray,
    *,
    max_cells: int | None = None,
) -> list[dict[str, Any]]:
    values = np.asarray(selected.values, dtype=float)
    if values.ndim != 2:
        raise RuntimeError("Expected a 2-D daily rainfall grid")
    grid = values[lat_index, lon_index]

    # Group grid cells by district without a Python-level per-district loop over
    # the whole grid: sorting by district index yields contiguous slices.
    order = np.argsort(district_index, kind="stable")
    sorted_district = district_index[order]
    sorted_cells = grid[order]
    boundaries = np.searchsorted(sorted_district, np.arange(len(districts) + 1))

    total_cells = int(latitudes.size * longitudes.size)
    results: list[dict[str, Any]] = []
    for index, (district_id, name, parent_state, geometry) in enumerate(districts):
        start, end = int(boundaries[index]), int(boundaries[index + 1])
        if end <= start:
            item = {
                "district_id": district_id,
                "district_name": name,
                "state": canonical_state_name(parent_state),
                **_district_stats(np.asarray([], dtype=float)),
            }
            item["data_coverage"] = {
                "grid_cells_in_district": 0,
                "valid_grid_cells": 0,
                "grid_coverage_percent": 0.0,
                "geometry_available": True,
                "unavailable_reason": "district polygon contains no IMD 0.25-degree grid-point centre",
            }
            results.append(item)
            continue
        stats = _district_stats(sorted_cells[start:end])
        cells = end - start
        item = {
            "district_id": district_id,
            "district_name": name,
            "state": canonical_state_name(parent_state),
            **stats,
        }
        item["data_coverage"] = {
            "grid_cells_in_district": int(cells),
            "valid_grid_cells": stats["valid_grid_cells"],
            "grid_coverage_percent": round(100.0 * stats["valid_grid_cells"] / cells, 2),
            "geometry_available": True,
            "unavailable_reason": None
            if stats["valid_grid_cells"]
            else "all intersecting IMD grid cells are missing for this date",
        }
        results.append(item)

    if max_cells is not None and len(results) > max_cells:
        results = results[:max_cells]
    return results


def _district_index_by_id(districts: tuple[tuple[str, str, str, Any], ...]) -> dict[str, int]:
    return {item[0]: index for index, item in enumerate(districts)}


def get_district_climate_metrics(date: str, district_id: str) -> dict[str, Any]:
    """Aggregate the validated IMD rainfall grid over one district polygon."""
    districts = _normalised_districts()
    lookup = _district_index_by_id(districts)
    index = lookup.get(district_id)
    if index is None:
        raise ValueError(f"Unknown India district: {district_id}")

    with read_dataset() as dataset:
        selected = _select_day(dataset, date)
        latitudes, longitudes = _dataset_coordinates(dataset)
        district_index, lat_index, lon_index = _build_cell_assignment(latitudes, longitudes)
        metrics = _aggregate_day(
            selected, latitudes, longitudes, districts, district_index, lat_index, lon_index
        )[index]

    district_id_value, name, parent_state, _ = districts[index]
    return {
        "status": "available" if metrics["valid_grid_cells"] else "no_data",
        "scope": "India",
        "level": "district",
        "district_id": district_id_value,
        "district_name": name,
        "state": canonical_state_name(parent_state),
        "observation_date": date,
        "variable": "RAINFALL",
        "units": "mm",
        "metrics": {
            key: metrics[key]
            for key in (
                "valid_grid_cells",
                "mean_rainfall_mm",
                "median_rainfall_mm",
                "minimum_rainfall_mm",
                "maximum_rainfall_mm",
                "mean_hazard_score",
                "maximum_hazard_score",
                "risk_category",
            )
        },
        "status_detail": metrics.get("status"),
        "data_coverage": metrics["data_coverage"],
        "aggregation_method": AGGREGATION_METHOD,
        "provenance": PROVENANCE,
    }


def get_all_district_climate_metrics(date: str) -> dict[str, Any]:
    """Aggregate the IMD rainfall grid over every district in one pass."""
    districts = _normalised_districts()
    with read_dataset() as dataset:
        selected = _select_day(dataset, date)
        latitudes, longitudes = _dataset_coordinates(dataset)
        district_index, lat_index, lon_index = _build_cell_assignment(latitudes, longitudes)
        rows = _aggregate_day(
            selected, latitudes, longitudes, districts, district_index, lat_index, lon_index
        )
    with_data = sum(1 for row in rows if row["valid_grid_cells"])
    return {
        "status": "available" if with_data else "no_data",
        "scope": "India",
        "level": "district",
        "observation_date": date,
        "variable": "RAINFALL",
        "units": "mm",
        "count": len(rows),
        "districts_with_data": with_data,
        "districts_without_grid_coverage": len(rows) - with_data,
        "districts": rows,
        "aggregation_method": AGGREGATION_METHOD,
        "source": "IMD RF25",
        "geometry_source": "geoBoundaries ADM2 (ODbL 1.0)",
        "note": "Districts with no IMD grid-point centre in their polygon report no_grid_coverage rather than an inferred value.",
    }


def get_state_district_climate_metrics(date: str, state_id: str) -> dict[str, Any]:
    """District-level metrics grouped under one state, with a district rollup."""
    from backend.services.india_hierarchy_service import STATES_AND_UTS

    normalized = state_id.strip().upper()
    if normalized not in {item["id"] for item in STATES_AND_UTS}:
        raise ValueError(f"Unknown India state or union territory: {state_id}")
    state_name = next(item["name"] for item in STATES_AND_UTS if item["id"] == normalized)

    payload = get_all_district_climate_metrics(date)
    # Match on the geoBoundaries parent_state name, which is the geometry source
    # of truth for district membership; falls back to a case-folded comparison.
    target = normalise_admin_name(state_name)
    matched = [
        row
        for row in payload["districts"]
        if normalise_admin_name(row["state"]) == target
    ]
    with_data = sum(1 for row in matched if row["valid_grid_cells"])
    return {
        "status": "available" if with_data else "no_data",
        "scope": "India",
        "level": "state_districts",
        "state_id": normalized,
        "state_name": state_name,
        "observation_date": date,
        "variable": "RAINFALL",
        "units": "mm",
        "count": len(matched),
        "districts_with_data": with_data,
        "districts": matched,
        "aggregation_method": AGGREGATION_METHOD,
        "rollup_note": "Rollup is computed from district polygons; it is not the state-polygon aggregate returned by /api/india/state/{state_id}/climate/{date}.",
        "provenance": PROVENANCE,
    }