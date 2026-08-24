from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.config.climate_config import (
    CLIMATE_VARIABLES,
)

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

# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="India Climate Digital Twin API",

    description=(
        "Scientific climate data API "
        "for the India Climate Digital Twin"
    ),

    version="0.3.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "project":
            "India Climate Digital Twin",

        "status":
            "online",

        "engine":
            "Python + FastAPI",

        "version":
            "0.3.0",
    }


# ============================================================
# API STATUS
# ============================================================

@app.get("/api/status")
def status():

    return {
        "status":
            "online",

        "data_source":
            "IMD",

        "scientific_engine":
            "Python + Xarray",

        "dataset":
            "RF25_ind2024_rfp25.nc",

        "variable":
            "RAINFALL",

        "stage":
            "Step 8K",
    }


# ============================================================
# DATASET INFORMATION
# ============================================================

@app.get("/api/rainfall/info")
def rainfall_info():

    try:

        return get_dataset_info()

    except Exception as error:

        raise HTTPException(
            status_code=500,

            detail=str(error),
        )


# ============================================================
# DAILY RAINFALL GRID
# ============================================================

@app.get(
    "/api/rainfall/daily/{date}"
)
def rainfall_daily(
    date: str
):

    try:

        return get_daily_rainfall(
            date
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,

            detail=str(error),
        )


# ============================================================
# DAILY RAINFALL STATISTICS
# ============================================================

@app.get(
    "/api/rainfall/statistics/{date}"
)
def rainfall_statistics(
    date: str
):

    try:

        return get_daily_statistics(
            date
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,

            detail=str(error),
        )


# ============================================================
# INDIA DAILY SUMMARY
# ============================================================

@app.get(
    "/api/rainfall/summary/{date}"
)
def rainfall_summary(
    date: str
):

    try:

        return get_india_daily_summary(
            date
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,

            detail=str(error),
        )


# ============================================================
# RAINFALL GRID AS GEOJSON
# ============================================================

@app.get(
    "/api/rainfall/grid/{date}"
)
def rainfall_grid(
    date: str
):

    try:

        return get_rainfall_grid(
            date
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,

            detail=str(error),
        )


# ============================================================
# RAINFALL GRID INFORMATION
# ============================================================

@app.get(
    "/api/rainfall/grid-info/{date}"
)
def rainfall_grid_info(
    date: str
):

    try:

        return get_rainfall_grid_info(
            date
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,

            detail=str(error),
        )
        # ============================================================
# CLIMATE VARIABLES
# ============================================================

@app.get("/api/climate/variables")
def climate_variables():

    return {
        "variables": CLIMATE_VARIABLES
    }
# ============================================================
# EXTREME RAINFALL EVENTS
# ============================================================

@app.get(
    "/api/extreme-events/rainfall/{date}"
)
def extreme_rainfall_events(
    date: str
):

    try:

        return detect_extreme_rainfall(
            date
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# EXTREME RAINFALL SUMMARY
# ============================================================

@app.get(
    "/api/extreme-events/summary/{date}"
)
def extreme_rainfall_summary(
    date: str
):

    try:

        return get_extreme_event_summary(
            date
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# EXTREME RAINFALL GEOJSON
# ============================================================

@app.get(
    "/api/extreme-events/rainfall/geojson/{date}"
)
def extreme_rainfall_geojson(
    date: str
):

    try:

        return get_extreme_rainfall_geojson(
            date
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# CLIMATE RISK SUMMARY
# ============================================================

@app.get(
    "/api/risk/summary/{date}"
)
def climate_risk_summary(
    date: str
):

    try:

        return get_climate_risk_summary(
            date
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# CLIMATE RISK GRID
# ============================================================

@app.get(
    "/api/risk/grid/{date}"
)
def climate_risk_grid(
    date: str
):

    try:

        return get_climate_risk_grid(
            date
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )