"""Authoritative source registry and local asset verification for the India Climate Twin."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMD_RAINFALL_FILE = PROJECT_ROOT / "backend" / "data" / "RF25_ind2024_rfp25.nc"

AUTHORITATIVE_SOURCES: list[dict[str, Any]] = [
    {"id": "imd-rainfall-rf25", "organization": "India Meteorological Department", "dataset": "0.25 degree daily gridded rainfall over India", "role": "observation", "status": "connected", "official_url": "https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html", "coverage": "India; 1901-2024 archive", "resolution": "0.25 degree", "unit": "mm", "local_asset": str(IMD_RAINFALL_FILE.relative_to(PROJECT_ROOT))},
    {"id": "mosdac-gsmap-isro", "organization": "ISRO Space Applications Centre / MOSDAC", "dataset": "GSMaP_ISRO Rain", "role": "satellite_observation", "status": "access_required", "official_url": "https://mosdac.gov.in/gsmap-isro-rain", "coverage": "March 2000 onward", "resolution": "0.1 degree; hourly", "unit": "gauge-adjusted precipitation product"},
    {"id": "mosdac-insat-rainfall", "organization": "ISRO Space Applications Centre / MOSDAC", "dataset": "INSAT rainfall products", "role": "satellite_observation", "status": "access_required", "official_url": "https://mosdac.gov.in/insat-3d-data-products", "coverage": "INSAT operational products", "resolution": "product dependent", "unit": "product dependent"},
    {"id": "era5-single-levels", "organization": "ECMWF / Copernicus Climate Change Service", "dataset": "ERA5 hourly single levels", "role": "reanalysis", "status": "access_required", "official_url": "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels", "coverage": "1940-present", "resolution": "dataset dependent", "unit": "variable dependent"},
    {"id": "nasa-merra2", "organization": "NASA", "dataset": "MERRA-2 reanalysis", "role": "forecast_model_input", "status": "contract_ready", "official_url": "https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/", "coverage": "1980-present", "resolution": "dataset dependent", "unit": "variable dependent"},
]


def _is_lfs_pointer(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            prefix = handle.read(64)
        return prefix.startswith(b"version https://git-lfs.github.com/spec/v1")
    except OSError:
        return False


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_local_assets() -> dict[str, Any]:
    """Verify that connected local assets are real files, not unresolved LFS pointers."""
    exists = IMD_RAINFALL_FILE.exists()
    size = IMD_RAINFALL_FILE.stat().st_size if exists else 0
    lfs_pointer = _is_lfs_pointer(IMD_RAINFALL_FILE) if exists else False
    verified = bool(exists and size > 0 and not lfs_pointer)
    return {
        "scope": "India",
        "verified": verified,
        "assets": [{
            "source_id": "imd-rainfall-rf25",
            "path": str(IMD_RAINFALL_FILE.relative_to(PROJECT_ROOT)),
            "exists": exists,
            "size_bytes": size,
            "unresolved_lfs_pointer": lfs_pointer,
            "sha256": _sha256(IMD_RAINFALL_FILE) if verified else None,
            "verification": "filesystem_presence_lfs_check_and_sha256",
        }],
        "policy": "An official URL alone does not make a source connected. The actual dataset asset must be present and resolvable.",
    }


def get_verified_sources() -> dict[str, Any]:
    return {
        "scope": "India",
        "sources": AUTHORITATIVE_SOURCES,
        "local_asset_verification": verify_local_assets(),
        "policy": "Only authoritative sources are eligible for the Digital Twin. Missing, unauthenticated, or unresolved sources remain unavailable rather than being replaced with synthetic data.",
    }
