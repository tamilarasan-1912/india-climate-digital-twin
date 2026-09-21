from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import time
from datetime import datetime, timezone

from backend.config.climate_config import CLIMATE_VARIABLES
from backend.services.rainfall_service import (
    get_dataset_info, get_daily_statistics, get_india_daily_summary,
    get_daily_rainfall, get_rainfall_grid, get_rainfall_grid_info,
)
from backend.services.extreme_event_service import (
    detect_extreme_rainfall, get_extreme_rainfall_geojson, get_extreme_event_summary,
)
from backend.services.climate_risk_service import get_climate_risk_summary, get_climate_risk_grid
from backend.services.digital_twin_service import (
    get_twin_state, get_historical_rainfall, get_baseline_forecast,
    get_model_catalog, get_validation_summary, explain_rainfall_risk,
    get_provenance, get_system_health,
)
from backend.services.model_registry import get_model_registry
from backend.services.twin_engine import build_twin_snapshot, build_what_next, build_what_if, get_twin_health
from backend.services.india_hierarchy_service import get_india_hierarchy, resolve_location
from backend.services.state_twin_service import get_all_state_climate_metrics, get_state_climate_metrics, get_state_twin, get_boundary_coverage
from backend.services.prithvi_wxc_service import get_prithvi_wxc_status, validate_prithvi_inputs, run_local_inference
from backend.services.climate_state_contract import get_climate_state_contract
from backend.services.multi_variable_twin_service import get_active_variable_catalog, get_variable_availability_report
from backend.services.climate_state_service import build_climate_state
from backend.services.merra2_tensor_service import inspect_input_file
from backend.services.prithvi_preprocessing_service import inspect_preprocessing
from backend.services.risk_contract import get_risk_contract
from backend.api.forecast_state_routes import generate_prithvi_forecast
from backend.services.forecast_service import get_grid_point_timeseries
from backend.services.validation_service import validate_risk_grid
from backend.api.platform_routes import router as platform_router
from backend.api.ogc_routes import router as ogc_router
from backend.api.data_routes import router as data_router
from backend.api.governance_routes import router as governance_router
from backend.api.prithvi_routes import router as prithvi_router
from backend.api.verified_data_routes import router as verified_data_router
from backend.services.climate_layer_service import get_climate_layer_catalog, get_layer_status, unavailable_layer
from backend.services.climate_provider import get_provider_registry, provider_config
from backend.services.climate_provider_runtime import get_provider_layer
from backend.services.climate_intelligence_service import answer_question, get_intelligence_capabilities
from backend.services.observability import configure_logging, new_request_id, request_id_var, log_request
from backend.services.auth_service import require_operator
from backend.services.rate_limiter import enforce_rate_limit
from backend.services.gods_eye_service import build_gods_eye_state, get_gods_eye_layer
from backend.services.administrative_boundary_service import get_admin_metadata, get_districts, get_district_geojson
from backend.services.district_climate_service import (
    get_all_district_climate_metrics,
    get_district_climate_metrics,
    get_district_geometry_coverage,
    get_state_district_climate_metrics,
)
from backend.services.climate_raster_service import raster_contract, tile_xyz_bounds, render_rainfall_xyz_tile

from backend.services.gods_eye_operations_service import (
    build_gods_eye_timeline, build_gods_eye_events, build_gods_eye_operations,
)

app = FastAPI(title="India Climate Digital Twin API", description="Operational scientific API for the India Climate Digital Twin.", version="1.7.0")
logger = logging.getLogger("climate.api")
configure_logging()
_cors_origins = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if origin.strip()]
if not _cors_origins:
    _cors_origins = ["http://localhost:3000"]
app.add_middleware(CORSMiddleware, allow_origins=_cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])
app.include_router(platform_router)
app.include_router(ogc_router)
app.include_router(data_router)
app.include_router(verified_data_router)
app.include_router(governance_router)
app.include_router(prithvi_router)

@app.middleware("http")
async def request_observability(request, call_next):
    token = request_id_var.set(request.headers.get("x-request-id") or new_request_id())
    started = time.perf_counter()
    try:
        enforce_rate_limit(request)
        response = await call_next(request)
    except HTTPException as error:
        # Rebuild the FastAPI error response so observability headers and the
        # request id are still applied on limiter rejections.
        response = JSONResponse({"detail": error.detail}, status_code=error.status_code)
    except Exception:
        logger.exception("unhandled request error")
        response = JSONResponse({"detail": "internal server error"}, status_code=500)
    try:
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["x-request-id"] = request_id_var.get()
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["x-frame-options"] = "DENY"
        response.headers["referrer-policy"] = "no-referrer"
        response.headers["cache-control"] = response.headers.get("cache-control", "no-store")
        log_request(
            endpoint=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            method=request.method,
        )
        return response
    finally:
        request_id_var.reset(token)


def _call(function, *args, **kwargs):
    """Invoke a service function and map its failures to HTTP semantics.

    Internal details are logged, not returned, so stack traces and filesystem
    paths do not leak to clients.
    """
    try:
        return function(*args, **kwargs)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (FileNotFoundError, RuntimeError) as error:
        logger.warning("service unavailable: %s", error)
        raise HTTPException(
            status_code=503,
            detail="Required scientific dataset, provider or model is unavailable.",
        ) from error
    except HTTPException:
        raise
    except Exception:
        logger.exception("service failure")
        raise HTTPException(status_code=500, detail="internal server error")


@app.exception_handler(FileNotFoundError)
async def _dataset_unavailable(request: Request, exc: FileNotFoundError):
    logger.warning("required dataset unavailable: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Required scientific dataset, provider or model is unavailable."},
    )


@app.exception_handler(RuntimeError)
async def _service_unavailable(request: Request, exc: RuntimeError):
    """Map unconfigured/unavailable dependencies to 503 across every router.

    Sub-routers such as ``platform_routes`` do not go through ``_call``, so a
    missing PostGIS database or provider would otherwise surface as an opaque
    500. Operational detail is logged, not returned.
    """
    logger.warning("dependency unavailable: %s", exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "Required scientific dataset, provider or model is unavailable."},
    )


@app.get("/")
def root():
    return {"project": "India Climate Digital Twin", "status": "online", "engine": "Python + FastAPI + India Climate Twin Core", "version": app.version}

@app.get("/api/status")
def status(): return get_system_health()

@app.get("/api/health")
def health(): return get_system_health()

@app.get("/api/ready")
def readiness():
    health_state = get_system_health()
    checks = health_state.get("checks", {})
    # The API can serve real science whenever the IMD observation dataset is
    # present. The Chennai twin/fused artefacts are metropolitan pilot data and
    # must not gate national readiness.
    required = {"imd_rainfall": bool(checks.get("imd_rainfall"))}
    ready = all(required.values())
    return {
        "status": "ready" if ready else "not_ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "required_checks": required,
        "optional_checks": {k: v for k, v in checks.items() if k not in required},
        "api_version": app.version,
    }

@app.get("/api/system/status")
def system_status():
    """Truthful per-capability status for the System console page and operators.

    Status is derived from observed data/model availability, never from the
    presence of an environment variable alone.
    """
    health_state = get_system_health()
    providers = get_provider_registry()["providers"]
    layer_catalog = get_climate_layer_catalog()["layers"]
    try:
        prithvi = get_prithvi_wxc_status()
        prithvi_state = {
            "status": prithvi["status"],
            "inference_ready": prithvi["inference_ready"],
            "blockers": prithvi["blockers"],
        }
    except Exception as error:
        prithvi_state = {"status": "error", "inference_ready": False, "blockers": [str(error)]}

    def capability(state: str, **extra):
        return {"state": state, **extra}

    capabilities = {
        "api": capability("CONNECTED", version=app.version),
        "imd_rainfall": capability(
            "CONNECTED" if health_state["checks"].get("imd_rainfall") else "NO_DATA",
            dataset="RF25_ind2024_rfp25.nc",
        ),
        "climate_providers": {
            key: capability(
                "PROVIDER REQUIRED" if not value["url_configured"] else "CONFIGURED (VALIDATION PENDING)",
                env_var=value["env_var"],
            )
            for key, value in providers.items()
            if key != "rainfall"
        },
        "risk_engine": capability("CONNECTED", scope="rainfall-only hazard screening"),
        "extreme_events": capability("CONNECTED", scope="IMD-derived rainfall events"),
        "twin_engine": capability("CONNECTED" if health_state["checks"].get("twin_state") else "DEGRADED"),
        "forecast": capability("AVAILABLE", model="7-day moving-average baseline", calibrated=False),
        "prithvi_wxc": capability("BLOCKED" if not prithvi_state["inference_ready"] else "CONNECTED", **prithvi_state),
        "validation": capability("VALIDATION REQUIRED", note="baseline rainfall forecast metrics available; no calibrated AI forecast metrics"),
        "district_climate": capability("AVAILABLE", note="district rainfall aggregated from real IMD grid cells covered by geoBoundaries ADM2 polygons; districts without intersecting grid centres report no_grid_coverage"),
        "flood_twin": capability("BLOCKED", note="no validated hydraulic model configured"),
        "ocean_and_land_layers": {
            key: capability("PROVIDER REQUIRED" if layer_catalog[key]["status"] != "connected" else "CONNECTED")
            for key in ("temperature", "lst", "sst", "anomalies")
        },
    }
    return {
        "contract": "india-climate-system-status/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall": "operational_with_declared_gaps",
        "capabilities": capabilities,
        "policy": "A configured provider URL is never reported as CONNECTED until it passes transport and schema validation.",
    }
@app.get("/api/climate/variables")
def climate_variables(): return {"variables": CLIMATE_VARIABLES}
@app.get("/api/climate/layers")
def climate_layers(): return get_climate_layer_catalog()
@app.get("/api/climate/layers/{layer}")
def climate_layer_status(layer: str, date: str = Query(..., min_length=10)): return _call(get_layer_status, layer, date)
@app.get("/api/climate/providers")
def climate_providers(): return get_provider_registry()
@app.get("/api/climate/providers/{layer}")
def climate_provider(layer: str): return _call(provider_config, layer)

@app.get("/api/climate/raster-contract/{layer}")
def climate_raster_contract(layer: str, date: str = Query(..., min_length=10)):
    definition = _call(get_climate_layer_catalog)["layers"].get(layer)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Unknown climate layer: {layer}")
    return raster_contract(layer=layer, provider=", ".join(definition["providers"]), variable=definition["variables"][0], units="provider-defined", source_path=None, date=date)

@app.get("/api/climate/tile-bounds/{z}/{x}/{y}")
def climate_tile_bounds(z: int, x: int, y: int):
    return {"z": z, "x": x, "y": y, "bbox": tile_xyz_bounds(z, x, y), "crs": "EPSG:4326"}

@app.get("/api/climate/tiles/rainfall/{date}/{z}/{x}/{y}.png")
def rainfall_xyz_tile(date: str, z: int, x: int, y: int):
    from backend.services.rainfall_service import DATA_FILE
    if not DATA_FILE.exists():
        raise HTTPException(status_code=503, detail="IMD rainfall source dataset is unavailable")
    return Response(
        content=_call(render_rainfall_xyz_tile, DATA_FILE, date, z, x, y),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )

# -------------------- GOD'S-EYE OPERATIONS --------------------
@app.get("/api/gods-eye/state")
def gods_eye_state(date: str = Query(..., min_length=10)):
    return _call(build_gods_eye_state, date)

@app.get("/api/gods-eye/layer/{layer}/{date}")
def gods_eye_layer(layer: str, date: str):
    return _call(get_gods_eye_layer, layer, date)

@app.get("/api/gods-eye/timeline")
def gods_eye_timeline(start: str = Query(..., min_length=10), end: str = Query(..., min_length=10), forecast_horizon: int = Query(default=7, ge=1, le=14)):
    return _call(build_gods_eye_timeline, start, end, forecast_horizon)

@app.get("/api/gods-eye/events/{date}")
def gods_eye_events(date: str):
    return _call(build_gods_eye_events, date)

@app.get("/api/gods-eye/operations/{date}")
def gods_eye_operations(date: str):
    return _call(build_gods_eye_operations, date)

@app.get("/api/climate/temperature/{date}")
def climate_temperature(date: str): return _call(get_provider_layer, "temperature", date)

@app.get("/api/climate/intelligence")
def climate_intelligence(question: str = Query(..., min_length=1), date: str = Query(..., min_length=10), layer: str = Query(default="rainfall")):
    return _call(answer_question, question, date, layer)

@app.get("/api/climate/intelligence/capabilities")
def climate_intelligence_capabilities():
    return get_intelligence_capabilities()
@app.get("/api/climate/lst/{date}")
def climate_lst(date: str): return _call(get_provider_layer, "lst", date)
@app.get("/api/climate/sst/{date}")
def climate_sst(date: str): return _call(get_provider_layer, "sst", date)
@app.get("/api/climate/anomalies/{date}")
def climate_anomalies(date: str): return _call(get_provider_layer, "anomalies", date)

# -------------------- DIGITAL TWIN CONTRACT --------------------
@app.get("/api/twin/contract")
def twin_contract(): return get_climate_state_contract()
@app.get("/api/twin/active-variables")
def twin_active_variables(): return {"variables": get_active_variable_catalog()}
@app.get("/api/twin/variables")
def twin_variables(): return _call(get_variable_availability_report)
@app.get("/api/twin/climate-state")
def twin_climate_state(date: str | None = Query(default=None, min_length=10)):
    return _call(build_climate_state, date)
@app.get("/api/risk/contract")
def risk_contract(): return get_risk_contract()

# -------------------- INDIA HIERARCHY --------------------
@app.get("/api/india/hierarchy")
def india_hierarchy(): return get_india_hierarchy()
@app.get("/api/india/location/{location_id}")
def india_location(location_id: str): return _call(resolve_location, location_id)
@app.get("/api/india/admin/metadata")
def india_admin_metadata(): return _call(get_admin_metadata)

@app.get("/api/india/districts")
def india_districts(state: str | None = Query(default=None, min_length=2)):
    return _call(get_districts, state)

@app.get("/api/india/districts/geojson")
def india_districts_geojson(state: str | None = Query(default=None, min_length=2)):
    return _call(get_district_geojson, state)

@app.get("/api/india/state/{state_id}/districts")
def india_state_districts(state_id: str):
    location = _call(resolve_location, state_id)
    return _call(get_districts, location["name"])

@app.get("/api/india/boundaries/coverage")
def india_boundary_coverage(): return _call(get_boundary_coverage)

@app.get("/api/india/state/{state_id}/districts/geojson")
def india_state_districts_geojson(state_id: str):
    location = _call(resolve_location, state_id)
    return _call(get_district_geojson, location["name"])

# -------------------- STATE CLIMATE TWIN --------------------
@app.get("/api/india/states/climate/{date}")
def india_states_climate(date: str): return _call(get_all_state_climate_metrics, date)
@app.get("/api/india/state/{state_id}/climate/{date}")
def india_state_climate(state_id: str, date: str): return _call(get_state_climate_metrics, date, state_id)
@app.get("/api/india/state/{state_id}/twin/{date}")
def india_state_twin(state_id: str, date: str): return _call(get_state_twin, date, state_id)

# -------------------- DISTRICT CLIMATE --------------------
# Aggregated from real IMD grid cells covered by real geoBoundaries ADM2 polygons.
@app.get("/api/india/districts/coverage")
def india_district_coverage(): return _call(get_district_geometry_coverage)

@app.get("/api/india/districts/climate/{date}")
def india_districts_climate(date: str): return _call(get_all_district_climate_metrics, date)

@app.get("/api/india/state/{state_id}/districts/climate/{date}")
def india_state_districts_climate(state_id: str, date: str):
    return _call(get_state_district_climate_metrics, date, state_id)

@app.get("/api/india/district/{district_id}/climate/{date}")
def india_district_climate(district_id: str, date: str):
    return _call(get_district_climate_metrics, date, district_id)

# -------------------- RAINFALL --------------------
@app.get("/api/rainfall/info")
def rainfall_info(): return _call(get_dataset_info)
@app.get("/api/rainfall/daily/{date}")
def rainfall_daily(date: str): return _call(get_daily_rainfall, date)
@app.get("/api/rainfall/statistics/{date}")
def rainfall_statistics(date: str): return _call(get_daily_statistics, date)
@app.get("/api/rainfall/summary/{date}")
def rainfall_summary(date: str): return _call(get_india_daily_summary, date)
@app.get("/api/rainfall/grid/{date}")
def rainfall_grid(date: str): return _call(get_rainfall_grid, date)
@app.get("/api/rainfall/grid-info/{date}")
def rainfall_grid_info(date: str): return _call(get_rainfall_grid_info, date)
@app.get("/api/rainfall/point")
def rainfall_point_timeseries(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    """Observed daily rainfall series for the nearest IMD grid cell.

    Returns an explicit `no_grid_coverage` status (HTTP 200) when the nearest
    cell falls outside the IMD land mask, instead of an unexplained null series.
    """
    return _call(get_grid_point_timeseries, latitude, longitude)

# -------------------- EXTREME EVENTS --------------------
@app.get("/api/extreme-events/rainfall/{date}")
def extreme_rainfall_events(date: str): return _call(detect_extreme_rainfall, date)
@app.get("/api/extreme-events/summary/{date}")
def extreme_rainfall_summary(date: str): return _call(get_extreme_event_summary, date)
@app.get("/api/extreme-events/rainfall/geojson/{date}")
def extreme_rainfall_geojson(date: str): return _call(get_extreme_rainfall_geojson, date)

# -------------------- RISK --------------------
@app.get("/api/risk/summary/{date}")
def climate_risk_summary(date: str): return _call(get_climate_risk_summary, date)
@app.get("/api/risk/grid/{date}")
def climate_risk_grid(date: str): return _call(get_climate_risk_grid, date)

# -------------------- CLIMATE DIGITAL TWIN --------------------
@app.get("/api/twin/health")
def twin_health(): return get_twin_health()
@app.get("/api/twin/summary")
def twin_summary(date: str | None = Query(default=None)): return _call(build_twin_snapshot, date)
@app.get("/api/twin/now")
def twin_now(date: str | None = Query(default=None)): return _call(build_twin_snapshot, date)
@app.get("/api/twin/next")
def twin_next(date: str | None = Query(default=None), horizon: int = Query(default=7, ge=1, le=14)): return _call(build_what_next, date, horizon)
@app.get("/api/twin/what-if")
def twin_what_if(base_date: str = Query(...), precipitation_delta_pct: float = Query(default=0.0, ge=-100, le=300), temperature_delta_c: float = Query(default=0.0, ge=-10, le=10), sea_level_rise_m: float = Query(default=0.0, ge=0, le=2), scenario: str = Query(default="custom", min_length=1, max_length=80)):
    return _call(build_what_if, base_date, precipitation_delta_pct, temperature_delta_c, sea_level_rise_m, scenario)
@app.get("/api/twin/state")
def twin_state(date: str | None = Query(default=None)): return _call(get_twin_state, date)

# -------------------- HISTORICAL ANALYTICS --------------------
@app.get("/api/historical/rainfall")
def historical_rainfall(start: str | None = Query(default=None), end: str | None = Query(default=None), limit: int = Query(default=365, ge=1, le=5000)):
    return _call(get_historical_rainfall, start, end, limit)

# -------------------- FORECAST --------------------
@app.get("/api/forecast/baseline")
def forecast_baseline(horizon: int = Query(default=7, ge=1, le=14)): return _call(get_baseline_forecast, horizon)
@app.get("/api/models")
def models(): return _call(get_model_catalog)
@app.get("/api/models/registry")
def model_registry(): return _call(get_model_registry)

# -------------------- PRITHVI WxC --------------------
@app.get("/api/ai/prithvi/status")
def prithvi_status(): return _call(get_prithvi_wxc_status)
@app.get("/api/ai/prithvi/validate")
def prithvi_validate(): return _call(validate_prithvi_inputs)
@app.post("/api/ai/prithvi/load")
def prithvi_load(request: Request):
    require_operator(request)
    return _call(run_local_inference)
@app.get("/api/ai/prithvi/input")
def prithvi_input(path: str | None = Query(default=None, min_length=1)):
    if not path:
        from backend.services.merra2_input_validator import discover_files
        files = discover_files()
        if not files:
            raise HTTPException(status_code=503, detail="No MERRA-2 NetCDF file is available in backend/data/merra2")
        path = str(files[-1])
    return _call(inspect_input_file, path)
@app.get("/api/ai/prithvi/preprocess")
def prithvi_preprocess(path: str | None = Query(default=None, min_length=1)):
    if not path:
        from backend.services.merra2_input_validator import discover_files
        files = discover_files()
        if not files:
            raise HTTPException(status_code=503, detail="No MERRA-2 NetCDF file is available in backend/data/merra2")
        path = str(files[-1])
    return _call(inspect_preprocessing, path)
@app.post("/api/ai/prithvi/forecast")
def prithvi_forecast(time_start: str = Query(..., min_length=10), time_end: str = Query(..., min_length=10), lead_time_hours: int = Query(default=6, ge=6, le=72)):
    return _call(generate_prithvi_forecast, time_start, time_end, lead_time_hours)

# -------------------- EXPLAINABILITY --------------------
@app.get("/api/explain/rainfall")
def explain_rainfall(rainfall_mm: float = Query(..., ge=0, le=10000)): return _call(explain_rainfall_risk, rainfall_mm)

# -------------------- SCENARIO / WHAT-IF --------------------
@app.get("/api/scenarios/simulate")
def scenario_simulate(base_date: str = Query(...), precipitation_delta_pct: float = Query(default=0.0, ge=-100, le=300), temperature_delta_c: float = Query(default=0.0, ge=-10, le=10), sea_level_rise_m: float = Query(default=0.0, ge=0, le=2), scenario: str = Query(default="custom", min_length=1, max_length=80)):
    return _call(build_what_if, base_date, precipitation_delta_pct, temperature_delta_c, sea_level_rise_m, scenario)

# -------------------- VALIDATION / PROVENANCE --------------------
@app.get("/api/validation")
def validation(): return _call(get_validation_summary)
@app.get("/api/validation/risk-consistency")
def validation_risk_consistency(date: str = Query(default="2024-07-15", min_length=10)):
    """Internal consistency checks for the rainfall hazard engine."""
    return _call(validate_risk_grid, date)
@app.get("/api/provenance")
def provenance(): return _call(get_provenance)
