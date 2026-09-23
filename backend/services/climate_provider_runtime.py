"""Runtime provider adapters for externally configured climate layers.

Providers are opt-in and validation-first: an HTTP endpoint is considered
usable only when it returns an application-compatible payload with provenance,
a valid time, spatial context, units, and the requested variable. No synthetic
values are generated and a configured URL is never treated as connected data.
"""
from __future__ import annotations

import json
import math
import os
from datetime import date as date_type, datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from backend.services.climate_layer_service import CLIMATE_LAYERS

ENV_BY_LAYER = {
    "temperature": "CLIMATE_PROVIDER_TEMPERATURE_URL",
    "lst": "CLIMATE_PROVIDER_LST_URL",
    "sst": "CLIMATE_PROVIDER_SST_URL",
    "anomalies": "CLIMATE_PROVIDER_ANOMALIES_URL",
}

# Names accepted by the adapter are deliberately explicit. The provider may
# use a scalar field, a GeoJSON feature property, or a documented alias, but a
# random JSON object is not promoted to scientific data.
EXPECTED_FIELDS: dict[str, tuple[str, ...]] = {
    "temperature": (
        "temperature",
        "temperature_c",
        "temperature_k",
        "air_temperature",
        "air_temperature_c",
        "air_temperature_k",
        "t2m",
    ),
    "lst": (
        "lst",
        "lst_c",
        "lst_k",
        "land_surface_temperature",
        "land_surface_temperature_c",
        "land_surface_temperature_k",
    ),
    "sst": (
        "sst",
        "sst_c",
        "sst_k",
        "sea_surface_temperature",
        "sea_surface_temperature_c",
        "sea_surface_temperature_k",
    ),
    "anomalies": (
        "anomaly",
        "anomaly_value",
        "temperature_anomaly",
        "precipitation_anomaly",
        "standardized_anomaly",
    ),
}


def _load_url(url: str, date: str, timeout: float) -> Any:
    sep = "&" if "?" in url else "?"
    request_url = f"{url}{sep}date={date}"
    request = Request(request_url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                raise RuntimeError(f"Provider returned HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Climate provider request failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("Climate provider returned invalid JSON") from exc


def _parse_timestamp(value: Any, *, fallback_date: str) -> str:
    """Return an ISO date for a provider timestamp or the requested date.

    The fallback is the date explicitly requested by the platform. It keeps
    simple provider adapters compatible while still validating that the
    request itself is an actual calendar date. If a provider supplies a
    timestamp, that timestamp must parse.
    """
    candidate = value if value not in (None, "") else fallback_date
    if isinstance(candidate, (int, float)):
        try:
            parsed = datetime.fromtimestamp(float(candidate), tz=timezone.utc)
        except (OverflowError, OSError, ValueError) as error:
            raise RuntimeError("Climate provider returned an invalid timestamp") from error
        return parsed.isoformat()
    text = str(candidate).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.isoformat()
    except ValueError:
        try:
            return date_type.fromisoformat(text).isoformat()
        except ValueError as error:
            raise RuntimeError("Climate provider returned an invalid timestamp") from error


def _feature_properties(payload: dict[str, Any]) -> list[dict[str, Any]]:
    features = payload.get("features")
    if features is None:
        return []
    if not isinstance(features, list):
        raise RuntimeError("Climate provider 'features' must be a list")
    properties: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            raise RuntimeError("Climate provider features must be objects")
        item = feature.get("properties", feature)
        if not isinstance(item, dict):
            raise RuntimeError("Climate provider feature properties must be objects")
        properties.append(item)
    return properties


def _has_spatial_context(payload: dict[str, Any]) -> bool:
    """Validate GeoJSON points or a documented spatial envelope/grid."""
    features = payload.get("features")
    if isinstance(features, list) and features:
        for feature in features:
            geometry = feature.get("geometry") if isinstance(feature, dict) else None
            if not isinstance(geometry, dict):
                return False
            coordinates = geometry.get("coordinates")
            if geometry.get("type") == "Point" and isinstance(coordinates, (list, tuple)) and len(coordinates) >= 2:
                try:
                    lon, lat = float(coordinates[0]), float(coordinates[1])
                except (TypeError, ValueError):
                    return False
                if math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90:
                    continue
            return False
        return True

    spatial = payload.get("spatial") or payload.get("bbox") or payload.get("grid")
    if spatial is None:
        # A provider can describe a national/grid response using coordinate
        # arrays instead of GeoJSON.
        return bool(payload.get("latitude") and payload.get("longitude"))
    if isinstance(spatial, dict):
        return bool(spatial.get("bbox") or spatial.get("latitude") or spatial.get("longitude") or spatial.get("geometry"))
    if isinstance(spatial, (list, tuple)):
        return len(spatial) in {4, 6}
    return False


def _has_expected_variable(payload: dict[str, Any], layer: str) -> bool:
    fields = set(EXPECTED_FIELDS[layer])
    candidates: list[dict[str, Any]] = [payload]
    candidates.extend(_feature_properties(payload))
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.append(data)
    return any(any(key in fields and value is not None for key, value in candidate.items()) for candidate in candidates)


def _units(payload: dict[str, Any]) -> str | None:
    provenance = payload.get("provenance")
    if isinstance(provenance, dict):
        value = provenance.get("units") or provenance.get("unit")
        if value not in (None, ""):
            return str(value)
    value = payload.get("units") or payload.get("unit")
    return str(value) if value not in (None, "") else None


def _validate_payload(payload: dict[str, Any], layer: str, requested_date: str) -> dict[str, Any]:
    """Validate the scientific shape before exposing provider values."""
    timestamp = _parse_timestamp(
        payload.get("timestamp") or payload.get("time") or payload.get("date"),
        fallback_date=requested_date,
    )
    data_available = bool(payload.get("data_available", "features" in payload or "data" in payload))
    if not data_available:
        return {
            "data_available": False,
            "timestamp": timestamp,
            "validation": "transport+schema+timestamp; no data returned",
        }

    if not _has_expected_variable(payload, layer):
        raise RuntimeError(f"Climate provider payload has no validated {layer} variable")
    if not _has_spatial_context(payload):
        raise RuntimeError("Climate provider payload has no valid spatial context")
    units = _units(payload)
    if not units:
        raise RuntimeError("Climate provider payload has no units")

    return {
        "data_available": True,
        "timestamp": timestamp,
        "units": units,
        "validation": "transport+schema+timestamp+spatial+variable+units",
    }


def get_provider_layer(layer: str, date: str) -> dict[str, Any]:
    key = layer.strip().lower()
    if key not in CLIMATE_LAYERS:
        raise ValueError(f"Unknown climate layer: {layer}")
    env = ENV_BY_LAYER.get(key)
    url = os.getenv(env, "").strip() if env else ""
    if not url:
        return {
            "layer": key,
            "date": date,
            "status": "NO_DATA",
            "data_available": False,
            "features": [],
            "provider_required": True,
            "env_var": env,
            "provenance": {
                "provider": None,
                "variable": CLIMATE_LAYERS[key]["variables"],
                "status": "provider_required",
            },
        }

    try:
        requested_date = date_type.fromisoformat(date).isoformat()
    except ValueError as error:
        raise ValueError(f"Invalid climate date: {date}") from error

    try:
        timeout = float(os.getenv("CLIMATE_PROVIDER_TIMEOUT_SECONDS", "15"))
    except ValueError as error:
        raise RuntimeError("CLIMATE_PROVIDER_TIMEOUT_SECONDS must be numeric") from error
    if timeout <= 0:
        raise RuntimeError("CLIMATE_PROVIDER_TIMEOUT_SECONDS must be positive")

    payload = _load_url(url, requested_date, timeout)
    if not isinstance(payload, dict):
        raise RuntimeError("Climate provider payload must be a JSON object")

    validation = _validate_payload(payload, key, requested_date)
    data_available = validation["data_available"]
    status = str(payload.get("status", "AVAILABLE"))

    payload.setdefault("layer", key)
    payload.setdefault("date", requested_date)
    payload["data_available"] = data_available
    payload["status"] = status if data_available else "NO_DATA"
    payload["validation"] = {
        **(payload.get("validation") if isinstance(payload.get("validation"), dict) else {}),
        **validation,
    }

    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    # Prefer the provider's own declared identity over a generic placeholder so
    # provenance keeps naming the real source, not this platform's config.
    declared_provider = (
        payload.get("provider")
        or provenance.get("provider")
        or os.getenv(f"{env}_NAME")
        or "configured-provider"
    )
    payload["provider"] = declared_provider
    provenance.setdefault("provider", declared_provider)
    provenance.setdefault("provider_url", url)
    provenance.setdefault("retrieved_at", datetime.now(timezone.utc).isoformat())
    provenance.setdefault("observation_time", validation["timestamp"])
    if validation.get("units"):
        provenance.setdefault("units", validation["units"])
    provenance.setdefault("validation", validation["validation"])
    payload["provenance"] = provenance
    return payload
