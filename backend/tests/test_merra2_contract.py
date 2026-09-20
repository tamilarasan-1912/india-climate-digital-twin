from __future__ import annotations

import numpy as np
import xarray as xr

from backend.services.merra2_contract_service import inspect_merra2_file


def test_merra2_inventory_detects_coordinates_and_cadence(tmp_path):
    path = tmp_path / "sample.nc"
    ds = xr.Dataset(
        {"temperature": (("time", "lat", "lon"), np.ones((2, 2, 2)))},
        coords={
            "time": np.array(["2026-01-01T00:00:00", "2026-01-01T06:00:00"], dtype="datetime64[ns]"),
            "lat": [10.0, 11.0],
            "lon": [76.0, 77.0],
        },
    )
    ds.to_netcdf(path)
    result = inspect_merra2_file(path)
    assert result["variable_count"] == 1
    assert result["latitude"]["name"] == "lat"
    assert result["longitude"]["name"] == "lon"
    assert result["time"]["count"] == 2
    assert result["time"]["interval_hours"] == 6.0
