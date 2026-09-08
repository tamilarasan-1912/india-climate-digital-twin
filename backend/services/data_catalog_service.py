"""Machine-readable catalog of India Climate Twin data contracts."""
from __future__ import annotations

from typing import Any

DATA_CATALOG: list[dict[str, Any]] = [
    {"id": "imd-rainfall", "variable": "rainfall", "source": "IMD", "role": "observation", "status": "connected", "spatial_scope": "India", "unit": "mm"},
    {"id": "era5", "variable": "atmospheric_reanalysis", "source": "ECMWF ERA5", "role": "reanalysis", "status": "partial", "spatial_scope": "India subset", "unit": "dataset-dependent"},
    {"id": "mosdac-insat", "variable": "satellite_products", "source": "ISRO MOSDAC", "role": "observation", "status": "planned_operational", "spatial_scope": "India and surrounding region", "unit": "product-dependent"},
    {"id": "merra2", "variable": "atmospheric_state", "source": "NASA MERRA-2", "role": "model_input", "status": "contract_ready", "spatial_scope": "India subset", "unit": "variable-dependent"},
    {"id": "prithvi-wxc", "variable": "weather_forecast", "source": "IBM/NASA Prithvi-WxC", "role": "forecast_model", "status": "asset_gated", "spatial_scope": "India subset", "unit": "variable-dependent"},
    {"id": "prithvi-eo", "variable": "earth_observation_features", "source": "IBM/NASA Prithvi-EO", "role": "satellite_ai", "status": "partial", "spatial_scope": "India locations", "unit": "feature-dependent"},
]


def get_data_catalog() -> dict[str, Any]:
    return {"scope": "India", "entries": DATA_CATALOG, "principle": "No data source is marked operational unless its validated ingestion path exists."}
