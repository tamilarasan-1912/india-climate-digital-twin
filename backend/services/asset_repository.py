"""PostGIS asset repository.

The API layer is intentionally stateless; assets are persisted in PostGIS when
DATABASE_URL is configured. No in-memory store is used as a fake production DB.
"""
from __future__ import annotations

import os
from typing import Any

from backend.models.domain_models import Asset


def _dsn() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is not configured; PostGIS asset persistence is unavailable")
    return value


def _connect():
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("psycopg is required for PostGIS persistence") from exc
    return psycopg.connect(_dsn())


def upsert_asset(asset: Asset) -> dict[str, Any]:
    sql = """
    INSERT INTO assets (
        asset_id, organization_id, location_id, asset_type, name, geom,
        elevation_m, replacement_cost_inr, annual_revenue_inr, criticality,
        attributes, updated_at
    ) VALUES (
        %(asset_id)s, %(organization_id)s, %(location_id)s, %(asset_type)s,
        %(name)s, ST_SetSRID(ST_Point(%(longitude)s, %(latitude)s), 4326),
        %(elevation_m)s, %(replacement_cost_inr)s, %(annual_revenue_inr)s,
        %(criticality)s, %(attributes)s::jsonb, now()
    )
    ON CONFLICT (asset_id) DO UPDATE SET
        name = EXCLUDED.name,
        asset_type = EXCLUDED.asset_type,
        location_id = EXCLUDED.location_id,
        geom = EXCLUDED.geom,
        elevation_m = EXCLUDED.elevation_m,
        replacement_cost_inr = EXCLUDED.replacement_cost_inr,
        annual_revenue_inr = EXCLUDED.annual_revenue_inr,
        criticality = EXCLUDED.criticality,
        attributes = EXCLUDED.attributes,
        updated_at = now()
    RETURNING asset_id;
    """
    import json

    params = asset.model_dump()
    params["asset_type"] = asset.asset_type.value
    params["attributes"] = json.dumps(asset.attributes)
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        conn.commit()
    return {"asset_id": row[0], "persisted": True}


def get_asset(asset_id: str) -> dict[str, Any] | None:
    sql = """
    SELECT asset_id, name, asset_type, organization_id::text, location_id,
           ST_Y(geom), ST_X(geom), elevation_m, replacement_cost_inr,
           annual_revenue_inr, criticality, attributes
    FROM assets WHERE asset_id = %s
    """
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (asset_id,))
            row = cur.fetchone()
    if not row:
        return None
    keys = [
        "asset_id", "name", "asset_type", "organization_id", "location_id",
        "latitude", "longitude", "elevation_m", "replacement_cost_inr",
        "annual_revenue_inr", "criticality", "attributes",
    ]
    return dict(zip(keys, row))
