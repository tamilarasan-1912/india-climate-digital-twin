"""Runtime provider adapters for externally configured climate layers.

Providers are opt-in and validation-first: an HTTP endpoint is considered
usable only when it returns an application-compatible payload with provenance.
No synthetic values are generated.
"""
from __future__ import annotations
import json, os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from typing import Any

from backend.services.climate_layer_service import CLIMATE_LAYERS

ENV_BY_LAYER = {
    "temperature": "CLIMATE_PROVIDER_TEMPERATURE_URL",
    "lst": "CLIMATE_PROVIDER_LST_URL",
    "sst": "CLIMATE_PROVIDER_SST_URL",
    "anomalies": "CLIMATE_PROVIDER_ANOMALIES_URL",
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

def get_provider_layer(layer: str, date: str) -> dict[str, Any]:
    key = layer.strip().lower()
    if key not in CLIMATE_LAYERS:
        raise ValueError(f"Unknown climate layer: {layer}")
    env = ENV_BY_LAYER.get(key)
    url = os.getenv(env, "").strip() if env else ""
    if not url:
        return {
            "layer": key, "date": date, "status": "NO_DATA",
            "data_available": False, "features": [],
            "provider_required": True, "env_var": env,
        }
    timeout = float(os.getenv("CLIMATE_PROVIDER_TIMEOUT_SECONDS", "15"))
    payload = _load_url(url, date, timeout)
    if not isinstance(payload, dict):
        raise RuntimeError("Climate provider payload must be a JSON object")
    status = str(payload.get("status", "AVAILABLE"))
    data_available = bool(payload.get("data_available", "features" in payload or "data" in payload))
    payload.setdefault("layer", key)
    payload.setdefault("date", date)
    payload.setdefault("provider", os.getenv(f"{env}_NAME", "configured-provider"))
    payload.setdefault("provenance", {
        "provider_url": url,
        "retrieved_at": None,
        "validation": "transport+schema",
    })
    payload["data_available"] = data_available
    payload["status"] = status if data_available else "NO_DATA"
    return payload
