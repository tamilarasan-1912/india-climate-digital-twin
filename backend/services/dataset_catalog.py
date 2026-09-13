"""STAC-oriented dataset catalog contract for the climate data plane."""
from __future__ import annotations

from typing import Any

CATALOG_VERSION = "1.0.0"


def build_dataset_record(
    *,
    dataset_id: str,
    provider: str,
    title: str,
    license: str | None,
    spatial_resolution: str | None,
    temporal_resolution: str | None,
    crs: str | None,
    object_uri: str,
    content_hash: str | None = None,
    stac_collection: str | None = None,
    stac_item: str | None = None,
    quality_score: float | None = None,
) -> dict[str, Any]:
    if not dataset_id or not provider or not object_uri:
        raise ValueError("dataset_id, provider and object_uri are required")
    if quality_score is not None and not 0 <= quality_score <= 1:
        raise ValueError("quality_score must be between 0 and 1")
    return {
        "catalog_version": CATALOG_VERSION,
        "dataset_id": dataset_id,
        "provider": provider,
        "title": title,
        "license": license,
        "spatial_resolution": spatial_resolution,
        "temporal_resolution": temporal_resolution,
        "crs": crs,
        "object_uri": object_uri,
        "content_hash": content_hash,
        "stac": {"collection": stac_collection, "item": stac_item},
        "quality_score": quality_score,
        "large_data_policy": "external_object_storage",
    }


def get_catalog_contract() -> dict[str, Any]:
    return {
        "version": CATALOG_VERSION,
        "standard": "STAC-compatible dataset metadata",
        "required_fields": [
            "dataset_id", "provider", "title", "object_uri",
            "license", "spatial_resolution", "temporal_resolution",
            "crs", "content_hash", "quality_score",
        ],
        "supported_formats": ["COG", "GeoTIFF", "NetCDF", "Zarr", "GeoJSON", "Parquet"],
        "lineage": "dataset -> processing -> model input -> twin state -> result",
    }
