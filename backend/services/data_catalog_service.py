"""Machine-readable catalog of India Climate Twin data contracts."""
from __future__ import annotations

from typing import Any

from backend.services.verified_data_service import AUTHORITATIVE_SOURCES, verify_local_assets

DATA_CATALOG: list[dict[str, Any]] = [
    {
        "id": "imd-rainfall",
        "variable": "rainfall",
        "source": "India Meteorological Department",
        "role": "observation",
        "status": "connected",
        "spatial_scope": "India",
        "unit": "mm",
        "official_url": "https://imdpune.gov.in/cmpg/Griddata/Rainfall_25_NetCDF.html",
    },
    {
        "id": "mosdac-gsmap-isro",
        "variable": "rainfall",
        "source": "ISRO MOSDAC",
        "role": "satellite_observation",
        "status": "access_required",
        "spatial_scope": "India and surrounding region",
        "unit": "product-dependent",
        "official_url": "https://mosdac.gov.in/gsmap-isro-rain",
    },
    {
        "id": "mosdac-insat",
        "variable": "satellite_products",
        "source": "ISRO MOSDAC",
        "role": "observation",
        "status": "access_required",
        "spatial_scope": "India and surrounding region",
        "unit": "product-dependent",
        "official_url": "https://mosdac.gov.in/insat-3d-data-products",
    },
    {
        "id": "era5",
        "variable": "atmospheric_reanalysis",
        "source": "ECMWF ERA5",
        "role": "reanalysis",
        "status": "access_required",
        "spatial_scope": "India subset",
        "unit": "dataset-dependent",
        "official_url": "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels",
    },
    {
        "id": "merra2",
        "variable": "atmospheric_state",
        "source": "NASA MERRA-2",
        "role": "model_input",
        "status": "contract_ready",
        "spatial_scope": "India subset",
        "unit": "variable-dependent",
        "official_url": "https://gmao.gsfc.nasa.gov/reanalysis/MERRA-2/",
    },
    {
        "id": "prithvi-wxc",
        "variable": "weather_forecast",
        "source": "IBM/NASA Prithvi-WxC",
        "role": "forecast_model",
        "status": "asset_gated",
        "spatial_scope": "India subset",
        "unit": "variable-dependent",
    },
    {
        "id": "prithvi-eo",
        "variable": "earth_observation_features",
        "source": "IBM/NASA Prithvi-EO",
        "role": "satellite_ai",
        "status": "partial",
        "spatial_scope": "India locations",
        "unit": "feature-dependent",
    },
]


def get_data_catalog() -> dict[str, Any]:
    return {
        "scope": "India",
        "entries": DATA_CATALOG,
        "authoritative_sources": AUTHORITATIVE_SOURCES,
        "local_asset_verification": verify_local_assets(),
        "principle": "No data source is marked operational unless its validated ingestion path exists.",
    }
