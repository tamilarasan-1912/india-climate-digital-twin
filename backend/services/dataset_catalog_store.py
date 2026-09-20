"""Small local STAC-compatible catalog index.

This is metadata storage only. Large scientific files remain external.
"""
from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any

CATALOG_ROOT = Path(os.getenv("CLIMATE_CATALOG_ROOT", "backend/data/catalog"))

def _catalog_file() -> Path:
    CATALOG_ROOT.mkdir(parents=True, exist_ok=True)
    return CATALOG_ROOT / "catalog.json"

def load_catalog() -> dict[str, Any]:
    path = _catalog_file()
    if not path.exists():
        return {"stac_version": "1.0.0", "type": "Catalog", "id": "bharat-climate-twin", "links": [], "items": []}
    return json.loads(path.read_text(encoding="utf-8"))

def register_dataset(record: dict[str, Any]) -> dict[str, Any]:
    catalog = load_catalog()
    items = catalog.setdefault("items", [])
    dataset_id = record["dataset_id"]
    items[:] = [item for item in items if item.get("dataset_id") != dataset_id]
    items.append(record)
    _catalog_file().write_text(json.dumps(catalog, indent=2, sort_keys=True), encoding="utf-8")
    return record

def search_datasets(
    *,
    provider: str | None = None,
    variable: str | None = None,
    text: str | None = None,
) -> list[dict[str, Any]]:
    records = load_catalog().get("items", [])
    out = []
    needle = text.lower().strip() if text else None
    for r in records:
        if provider and str(r.get("provider", "")).lower() != provider.lower():
            continue
        if variable and variable.lower() not in {str(v).lower() for v in r.get("variables", [])}:
            continue
        if needle and needle not in json.dumps(r).lower():
            continue
        out.append(r)
    return out
