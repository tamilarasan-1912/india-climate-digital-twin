"""Reusable spatial aggregation primitives for India administrative twins."""
from __future__ import annotations

from typing import Any
import numpy as np
from shapely.geometry import Point, shape


def aggregate_grid_to_feature(values: np.ndarray, latitudes: np.ndarray, longitudes: np.ndarray, feature: dict[str, Any]) -> dict[str, Any]:
    """Aggregate a 2-D grid over cells whose centers fall inside a polygon."""
    array = np.asarray(values, dtype=float)
    if array.ndim != 2:
        raise ValueError("values must be a 2-D latitude/longitude grid")
    if array.shape != (len(latitudes), len(longitudes)):
        raise ValueError("grid dimensions do not match latitude/longitude coordinates")
    geometry = shape(feature["geometry"])
    selected: list[float] = []
    for i, lat in enumerate(latitudes):
        for j, lon in enumerate(longitudes):
            if geometry.covers(Point(float(lon), float(lat))) and np.isfinite(array[i, j]):
                selected.append(float(array[i, j]))
    if not selected:
        return {"status": "no_data", "valid_grid_cells": 0}
    arr = np.asarray(selected)
    return {
        "status": "available",
        "valid_grid_cells": int(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "minimum": float(np.min(arr)),
        "maximum": float(np.max(arr)),
        "std": float(np.std(arr)),
        "selection_method": "grid-cell-center polygon coverage",
    }
