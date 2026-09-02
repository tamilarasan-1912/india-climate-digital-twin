from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.config.climate_config import CLIMATE_VARIABLES
from backend.services.rainfall_service import (
    get_dataset_info,
    get_daily_statistics,
    get_india_daily_summary,
    get_daily_rainfall,
    get_rainfall_grid,
    get_rainfall_grid_info,
)
from backend.services.extreme_event_service import (
    detect_extreme_rainfall,
    get_extreme_rainfall_geojson,
    get_extreme_event_summary,
)
from backend.services.climate_risk_service import (
    get_climate_risk_summary,
    get_climate_risk_grid,
)
from backend.services.digital_twin_service import (
    get_twin_state,
    get_historical_rainfall,
    get_baseline_forecast,
    get_model_catalog,
    get_validation_summary,
    explain_rainfall_risk,
    get_provenance,
    get_system_health,
)
from backend.services.twin_engine import (
    build_twin_snapshot,
    build_what_next,
    build_what_if,
    get_twin_health,
)
from backend.services.prithvi_wxc_service import (
    get_prithvi_wxc_status,
    validate_prithvi_inputs,
    run_local_inference,
)

app = FastAPI(
    title="India Climate Digital Twin API",
    description="Operational scientific API for the India Climate Digital Twin.",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _call(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


@app.get("/")
def root():
    return {
        "project": "India Climate Digital Twin",
        "status": "online",
        "engine": "Python + FastAPI + Climate Twin Engine",
        "version": "0.6.0",
    }


@app.get("/api/status")
def status():
    return get_system_health()


@app.get("/api/health")
def health():
    return get_system_health()


@app.get("/api/climate/variables")
def climate_variables():
    return {"variables": CLIMATE_VARIABLES}


@app.get("/api/rainfall/info")
def rainfall_info():
    return _call(get_dataset_info)


@app.get("/api/rainfall/daily/{date}")
def rainfall_daily(date: str):
    return _call(get_daily_rainfall, date)


@app.get("/api/rainfall/statistics/{date}")
def rainfall_statistics(date: str):
    return _call(get_daily_statistics, date)


@app.get("/api/rainfall/summary/{date}")
def rainfall_summary(date: str):
    return _call(get_india_daily_summary, date)


@app.get("/api/rainfall/grid/{date}")
def rainfall_grid(date: str):
    return _call(get_rainfall_grid, date)


@app.get("/api/rainfall/grid-info/{date}")
def rainfall_grid_info(date: str):
    return _call(get_rainfall_grid_info, date)


@app.get("/api/extreme-events/rainfall/{date}")
def extreme_rainfall_events(date: str):
    return _call(detect_extreme_rainfall, date)


@app.get("/api/extreme-events/summary/{date}")
def extreme_rainfall_summary(date: str):
    return _call(get_extreme_event_summary, date)


@app.get("/api/extreme-events/rainfall/geojson/{date}")
def extreme_rainfall_geojson(date: str):
    return _call(get_extreme_rainfall_geojson, date)


@app.get("/api/risk/summary/{date}")
def climate_risk_summary(date: str):
    return _call(get_climate_risk_summary, date)


@app.get("/api/risk/grid/{date}")
def climate_risk_grid(date: str):
    return _call(get_climate_risk_grid, date)


# -------------------- CLIMATE DIGITAL TWIN --------------------

@app.get("/api/twin/health")
def twin_health():
    return get_twin_health()


@app.get("/api/twin/summary")
def twin_summary(date: str | None = Query(default=None)):
    return _call(build_twin_snapshot, date)


@app.get("/api/twin/now")
def twin_now(date: str | None = Query(default=None)):
    return _call(build_twin_snapshot, date)


@app.get("/api/twin/next")
def twin_next(
    date: str | None = Query(default=None),
    horizon: int = Query(default=7, ge=1, le=14),
):
    return _call(build_what_next, date, horizon)


@app.get("/api/twin/what-if")
def twin_what_if(
    base_date: str = Query(...),
    precipitation_delta_pct: float = Query(default=0.0, ge=-100, le=300),
    temperature_delta_c: float = Query(default=0.0, ge=-10, le=10),
    sea_level_rise_m: float = Query(default=0.0, ge=0, le=2),
    scenario: str = Query(default="custom", min_length=1, max_length=80),
):
    return _call(
        build_what_if,
        base_date,
        precipitation_delta_pct,
        temperature_delta_c,
        sea_level_rise_m,
        scenario,
    )


@app.get("/api/twin/state")
def twin_state(date: str | None = Query(default=None)):
    return _call(get_twin_state, date)


# -------------------- HISTORICAL ANALYTICS --------------------

@app.get("/api/historical/rainfall")
def historical_rainfall(
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    limit: int = Query(default=365, ge=1, le=5000),
):
    return _call(get_historical_rainfall, start, end, limit)


# -------------------- FORECAST --------------------

@app.get("/api/forecast/baseline")
def forecast_baseline(
    horizon: int = Query(default=7, ge=1, le=14),
):
    return _call(get_baseline_forecast, horizon)


@app.get("/api/models")
def models():
    return _call(get_model_catalog)


# -------------------- PRITHVI WxC --------------------

@app.get("/api/ai/prithvi/status")
def prithvi_status():
    return _call(get_prithvi_wxc_status)


@app.get("/api/ai/prithvi/validate")
def prithvi_validate():
    return _call(validate_prithvi_inputs)


@app.post("/api/ai/prithvi/load")
def prithvi_load():
    return _call(run_local_inference)


# -------------------- EXPLAINABILITY --------------------

@app.get("/api/explain/rainfall")
def explain_rainfall(
    rainfall_mm: float = Query(..., ge=0, le=10000),
):
    return _call(explain_rainfall_risk, rainfall_mm)


# -------------------- SCENARIO / WHAT-IF --------------------

@app.get("/api/scenarios/simulate")
def scenario_simulate(
    base_date: str = Query(...),
    precipitation_delta_pct: float = Query(default=0.0, ge=-100, le=300),
    temperature_delta_c: float = Query(default=0.0, ge=-10, le=10),
    sea_level_rise_m: float = Query(default=0.0, ge=0, le=2),
    scenario: str = Query(default="custom", min_length=1, max_length=80),
):
    return _call(
        build_what_if,
        base_date,
        precipitation_delta_pct,
        temperature_delta_c,
        sea_level_rise_m,
        scenario,
    )


# -------------------- VALIDATION / PROVENANCE --------------------

@app.get("/api/validation")
def validation():
    return _call(get_validation_summary)


@app.get("/api/provenance")
def provenance():
    return _call(get_provenance)
