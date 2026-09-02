"""India administrative hierarchy for the climate digital twin.

The twin uses a fixed national -> state -> district -> city hierarchy.
Administrative climate metrics are only reported when a validated dataset is
available for that level; this module does not fabricate district/city data.
"""

from __future__ import annotations

from typing import Any


INDIA = {"id": "IN", "name": "India", "level": "country"}

STATES_AND_UTS: tuple[dict[str, str], ...] = (
    {"id": "IN-AP", "name": "Andhra Pradesh"},
    {"id": "IN-AR", "name": "Arunachal Pradesh"},
    {"id": "IN-AS", "name": "Assam"},
    {"id": "IN-BR", "name": "Bihar"},
    {"id": "IN-CT", "name": "Chhattisgarh"},
    {"id": "IN-GA", "name": "Goa"},
    {"id": "IN-GJ", "name": "Gujarat"},
    {"id": "IN-HR", "name": "Haryana"},
    {"id": "IN-HP", "name": "Himachal Pradesh"},
    {"id": "IN-JK", "name": "Jammu and Kashmir"},
    {"id": "IN-JH", "name": "Jharkhand"},
    {"id": "IN-KA", "name": "Karnataka"},
    {"id": "IN-KL", "name": "Kerala"},
    {"id": "IN-LA", "name": "Ladakh"},
    {"id": "IN-MP", "name": "Madhya Pradesh"},
    {"id": "IN-MH", "name": "Maharashtra"},
    {"id": "IN-MN", "name": "Manipur"},
    {"id": "IN-ML", "name": "Meghalaya"},
    {"id": "IN-MZ", "name": "Mizoram"},
    {"id": "IN-NL", "name": "Nagaland"},
    {"id": "IN-OR", "name": "Odisha"},
    {"id": "IN-PB", "name": "Punjab"},
    {"id": "IN-RJ", "name": "Rajasthan"},
    {"id": "IN-SK", "name": "Sikkim"},
    {"id": "IN-TN", "name": "Tamil Nadu"},
    {"id": "IN-TG", "name": "Telangana"},
    {"id": "IN-TR", "name": "Tripura"},
    {"id": "IN-UP", "name": "Uttar Pradesh"},
    {"id": "IN-UK", "name": "Uttarakhand"},
    {"id": "IN-WB", "name": "West Bengal"},
    {"id": "IN-AN", "name": "Andaman and Nicobar Islands"},
    {"id": "IN-CH", "name": "Chandigarh"},
    {"id": "IN-DH", "name": "Dadra and Nagar Haveli and Daman and Diu"},
    {"id": "IN-DL", "name": "Delhi"},
    {"id": "IN-LD", "name": "Lakshadweep"},
    {"id": "IN-PY", "name": "Puducherry"},
)


def _node(item: dict[str, str], level: str, parent_id: str = "IN") -> dict[str, Any]:
    return {
        "id": item["id"],
        "name": item["name"],
        "level": level,
        "parent_id": parent_id,
        "status": "metadata_only",
        "children_available": False,
        "data_status": "NO DATA until a validated administrative dataset is connected",
    }


def get_india_hierarchy() -> dict[str, Any]:
    """Return the national hierarchy contract and available administrative nodes."""
    return {
        "status": "available",
        "scope": "India",
        "levels": ["country", "state", "district", "city"],
        "country": INDIA,
        "states_and_union_territories": [
            _node(item, "state", "IN") for item in STATES_AND_UTS
        ],
        "districts": [],
        "cities": [],
        "data_policy": "Never infer or fabricate district/city climate metrics from national aggregates.",
    }


def resolve_location(location_id: str) -> dict[str, Any]:
    """Resolve an India location id and report its current data availability."""
    normalized = location_id.strip().upper()
    if normalized == "IN":
        return {**INDIA, "status": "available", "data_status": "India-wide climate data available"}

    for item in STATES_AND_UTS:
        if item["id"] == normalized:
            return _node(item, "state") | {
                "data_status": "state geometry available; climate aggregation is not yet connected"
            }

    raise ValueError(f"Unknown India location id: {location_id}")
