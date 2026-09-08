# India Climate Digital Twin

An AI-ready geospatial climate intelligence platform for India. The project implements an **India Climate Digital Twin core** built around validated observations, an auditable synchronized state, forecasting, hazard assessment, scenario analysis, provenance, validation and map-based decision support.

> **Scope:** India is the system boundary. International Earth-system Digital Twin programmes are used as scientific/engineering references, not as the project's scope.

## What makes this a Digital Twin

A dashboard, GIS, simulation or ML model alone is not a Digital Twin. This project follows the operational pattern:

**Real-world India climate observations → ingestion/QC → synchronized digital state → analysis/forecasting → scenario experimentation → decision support → state update**

NIST describes a Digital Twin as a virtual representation of a real-world entity and emphasizes dynamic connection and synchronization, while its Digital Twin guidance highlights prediction, simulation and decision support. The climate-twin interpretation is adapted here to India's weather/climate state and the observations that are actually available. See `docs/DIGITAL_TWIN_RESEARCH.md` for the research basis.

## Current implementation

- Next.js + React frontend with MapLibre-based India map UI
- FastAPI + Xarray/NumPy scientific backend
- IMD RF25 gridded rainfall ingestion, statistics, grids and GeoJSON
- Extreme-rainfall classification and spatial event layers
- Rainfall hazard-risk scoring and validation
- India administrative hierarchy with state-level twin APIs
- Chennai Sentinel-2 historical archive and Prithvi-EO input pipeline
- Chennai Prithvi-EO + ERA5 fused feature matrix and deterministic feature-state experiment
- **Climate Twin Engine v1.0** with synchronized What-Now state, What-Next forecast and What-If sensitivity analysis
- 7-day moving-average rainfall baseline with walk-forward MAE/RMSE/Bias evaluation
- Provenance, model registry, validation and explainability APIs
- GitHub Actions CI for frontend build and backend checks
- Vercel frontend + Render FastAPI deployment architecture

## Digital Twin API

| Capability | Endpoint |
|---|---|
| Twin health | `/api/twin/health` |
| What Now / synchronized twin | `/api/twin/now` |
| Twin summary | `/api/twin/summary` |
| What Next | `/api/twin/next?horizon=7` |
| What If | `/api/twin/what-if?...` |
| Twin vector | `/api/twin/state` |
| India hierarchy | `/api/india/hierarchy` |
| State location | `/api/india/location/{location_id}` |
| State climate twin | `/api/india/state/{state_id}/twin/{date}` |
| General health | `/api/health` |
| Climate variables | `/api/climate/variables` |
| Rainfall | `/api/rainfall/*` |
| Extreme events | `/api/extreme-events/*` |
| Risk | `/api/risk/*` |
| Historical | `/api/historical/rainfall` |
| Baseline forecast | `/api/forecast/baseline` |
| Model registry | `/api/models` |
| Explainability | `/api/explain/rainfall` |
| Scenario compatibility | `/api/scenarios/simulate` |
| Validation | `/api/validation` |
| Provenance | `/api/provenance` |

## Digital Twin state

The operational state is deliberately auditable rather than a fabricated AI latent state. For a selected observation date it contains, where the required source data exists:

- spatial rainfall statistics;
- 7-day rolling rainfall state;
- 30-day anomaly and anomaly z-score;
- rainfall-hazard mean and maximum;
- spatial risk distribution;
- maximum-risk location;
- administrative location context;
- source, variable, unit and observation date;
- state hash and observation coverage;
- model/data provenance;
- explicit data freshness and availability status.

The state is regenerated from source observations, so it can be synchronized again when the underlying observation state changes.

## Forecasting and model honesty

The current production-safe forecast is the validated 7-day moving-average rainfall baseline. It provides a reproducible benchmark while the Prithvi-WxC input pipeline is being completed.

**Prithvi-WxC is not presented as operational until its official multi-variable MERRA-2 input contract is satisfied.** The existing IMD rainfall-only dataset is not substituted for those atmospheric inputs.

Forecast responses identify the model, forecast origin, horizon and current calibration limitation. Missing uncertainty estimates are labelled rather than invented.

## What-If scenarios

The current scenario engine performs a rainfall-hazard sensitivity experiment. It can perturb precipitation and recompute the rainfall hazard field. Temperature and sea-level inputs are retained as scenario parameters but are explicitly marked as **uncoupled** until validated temperature and coastal/flood models are connected.

Therefore:

- observed state ≠ forecast;
- forecast ≠ hypothetical scenario;
- rainfall sensitivity ≠ physical flood simulation.

## Data strategy

| Source | Current role | Status |
|---|---|---|
| IMD RF25 | India rainfall observations | Connected |
| ERA5 | Chennai feature-fusion research | Connected for research subset |
| Sentinel-2 | EO history / Prithvi-EO input | Connected for research subset |
| MOSDAC / ISRO | Indian EO/meteorological products | Provider identified; product-specific integration gated by access/validation |
| Prithvi-EO | EO representation experiment | Connected for prepared research data |
| Prithvi-WxC | Multi-variable weather/climate forecasting | Contract/status integrated; inference gated until valid MERRA-2 inputs are present |

The project never substitutes random or synthetic values for unavailable observations.

## Architecture

```text
REAL-WORLD INDIA CLIMATE
        │
        ├── IMD observations
        ├── Satellite / EO
        ├── Reanalysis
        └── Forecast products
        │
        ▼
DATA INGESTION + VALIDATION + PROVENANCE
        │
        ▼
INDIA DIGITAL TWIN STATE
        │  location + time + variable + value
        │  source + freshness + confidence/uncertainty
        │
        ├──────────────┬───────────────┬───────────────┐
        ▼              ▼               ▼               ▼
   Risk engine     Forecasting     EO/ML features   Scenario engine
        │              │               │               │
        └──────────────┴───────────────┴───────────────┘
                              │
                              ▼
                    TWIN API / MODEL API
                              │
                              ▼
                MAP + TIME SERIES + DECISION UI
                              │
                              ▼
                       HUMAN DECISION SUPPORT
```

See `docs/DIGITAL_TWIN_RESEARCH.md` and `docs/INDIA_CLIMATE_TWIN_ARCHITECTURE.md` for the research and implementation details.

## Local development

```bash
# backend
python -m uvicorn backend.api.main:app --reload --port 8000

# frontend, in another terminal
npm run dev

# validation
python -m compileall backend scripts
npm run build
```

## Production architecture

- GitHub: source control and reproducible history
- Vercel: Next.js frontend
- Render: FastAPI scientific backend
- External/object storage: large climate datasets and the 28+ GB Prithvi-WxC checkpoint
- MapLibre: geospatial visualization
- Xarray/NumPy: scientific processing

## Scientific limitations

This repository is an operational **core**, not a claim of equivalence with global programmes such as Destination Earth. A mature national climate twin still requires continuous multi-variable observations, data assimilation, calibrated probabilistic forecasting, hydrology/coastal/land-surface coupling, uncertainty quantification, stronger temporal validation, operational ingestion and substantially larger compute/storage infrastructure.
