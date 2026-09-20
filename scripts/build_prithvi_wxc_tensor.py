"""Build a validated Prithvi-WxC tensor from an official preprocessed package.

This module intentionally refuses to guess variable order or normalization.
Provide a JSON mapping containing the official 160-variable order and verified
mean/std statistics. The resulting array is written as float32 NCHW-like data
with time first: [2, 160, lat, lon].
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import xarray as xr

EXPECTED_VARIABLES = 160
EXPECTED_TIMES = 2


def load_contract(path: Path) -> tuple[list[str], np.ndarray, np.ndarray]:
    data = json.loads(path.read_text(encoding="utf-8"))
    names = data.get("variables")
    mean = data.get("mean")
    std = data.get("std")
    if not isinstance(names, list) or len(names) != EXPECTED_VARIABLES:
        raise ValueError("Official contract must provide exactly 160 variable names in model order")
    if not isinstance(mean, list) or not isinstance(std, list) or len(mean) != EXPECTED_VARIABLES or len(std) != EXPECTED_VARIABLES:
        raise ValueError("Official contract must provide 160 mean and 160 std values")
    mean_arr = np.asarray(mean, dtype=np.float32)
    std_arr = np.asarray(std, dtype=np.float32)
    if np.any(~np.isfinite(mean_arr)) or np.any(~np.isfinite(std_arr)) or np.any(std_arr <= 0):
        raise ValueError("Mean/std statistics must be finite and std must be positive")
    return names, mean_arr, std_arr


def build(input_path: Path, contract_path: Path, output_path: Path) -> dict:
    names, mean, std = load_contract(contract_path)
    with xr.open_dataset(input_path, decode_times=True) as ds:
        missing = [name for name in names if name not in ds.data_vars]
        extra = [name for name in ds.data_vars if name not in names]
        if missing or extra:
            raise ValueError(f"Variable contract mismatch; missing={missing[:5]} extra={extra[:5]}")
        time_name = next((n for n in ("time", "valid_time", "TIME") if n in ds.coords or n in ds.dims), None)
        if not time_name or ds.sizes[time_name] != EXPECTED_TIMES:
            raise ValueError(f"Expected exactly 2 timestamps; found {ds.sizes.get(time_name, 0) if time_name else 0}")
        arrays = []
        for name, mu, sigma in zip(names, mean, std):
            values = ds[name].transpose(time_name, ...).values.astype(np.float32)
            if values.shape[0] != EXPECTED_TIMES:
                raise ValueError(f"Variable {name} does not contain two time slices")
            if not np.isfinite(values).all():
                raise ValueError(f"Variable {name} contains NaN/Inf values")
            arrays.append((values - mu) / sigma)
        tensor = np.stack(arrays, axis=1).astype(np.float32, copy=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(output_path, tensor)
        manifest = {
            "input": str(input_path),
            "contract": str(contract_path),
            "output": str(output_path),
            "shape": list(tensor.shape),
            "dtype": str(tensor.dtype),
            "variable_count": EXPECTED_VARIABLES,
            "timestamp_count": EXPECTED_TIMES,
            "normalization": "official mean/std from supplied contract",
            "synthetic_data": False,
        }
        output_path.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return manifest


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = build(args.input, args.contract, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
