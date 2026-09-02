# India Climate Digital Twin

An AI-ready geospatial climate intelligence platform for India. The project now implements an operational **climate digital-twin core** built around validated IMD gridded rainfall, Chennai ERA5 + Prithvi-EO fused features, a deterministic observation-derived twin state, extreme-rainfall detection, a rainfall hazard-risk engine, forecasting and what-if analysis.

## How the digital twin works

The system follows the Earth-system digital-twin pattern used by NASA Earth System Digital Twin work and Destination Earth:

**Observed Earth system -> validation/QC -> synchronized digital state -> forecasting + impact models -> What Now / What Next / What If -> decision support**

The climate twin is not a static map and not just an AI model. Its state is regenerated from source observations, identified with a state hash, accompanied by provenance, and passed into forecasting and scenario engines.

## Current implementation

- Next.js + React frontend with MapLibre-based map UI
- FastAPI + Xarray scientific backend
- IMD rainfall NetCDF ingestion, statistics, grids and GeoJSON
- Extreme rainfall classification and spatial event layers
- Rainfall hazard-risk scoring and validation
- Chennai Sentinel-2 historical archive and validated Prithvi-EO input pipeline
- Chennai Prithvi-EO + ERA5 fused feature matrix
- 128-D deterministic Digital Twin State from the existing fused observations
- **Climate Twin Engine v1.0** with synchronized What-Now state, What-Next forecast and What-If scenario computation
- 7-day moving-average rainfall baseline with walk-forward MAE/RMSE/Bias
- Operational APIs for twin state, twin health, historical analytics, baseline forecast, scenarios, explainability, provenance and validation
- GitHub Actions CI for frontend build and backend import/compile checks

## Digital Twin API

| Capability | Endpoint |
|---|---|
| Twin health | `/api/twin/health` |
| What Now / synchronized twin | `/api/twin/now` |
| Twin summary | `/api/twin/summary` |
| What Next | `/api/twin/next?horizon=7` |
| What If | `/api/twin/what-if?...` |
| Twin vector | `/api/twin/state` |
| General health | `/api/health` |
| Climate variables | `/api/climate/variables` |
| Rainfall | `/api/rainfall/*` |
| Extreme events | `/api/extreme-events/*` |
| Risk | `/api/risk/*` |
| Historical | `/api/historical/rainfall` |
| Baseline forecast | `/api/forecast/baseline` |
| Model registry | `/api/models` |
| Explainability | `/api/explain/rainfall` |
| Scenario compatibility endpoint | `/api/scenarios/simulate` |
| Validation | `/api/validation` |
| Provenance | `/api/provenance` |

## What the current twin state contains

For a selected IMD observation date, the engine derives:

- rainfall minimum, median, mean and maximum;
- 7-day rolling mean;
- 30-day anomaly and anomaly z-score;
- spatial mean and maximum rainfall hazard;
- spatial risk distribution;
- maximum-risk location;
- compact observation-derived state vector;
- deterministic state hash;
- source dataset and model provenance.

This is deliberately described as an **observation-derived state**, not as a learned neural latent state.

## Scientific honesty and model gating

Prithvi-WxC is not used as a fake forecast. Its official multi-variable atmospheric input contract must be satisfied before inference is enabled. The current IMD rainfall-only dataset is not a valid substitute for that input.

Likewise, temperature, population exposure, flood physics, sea-level impacts and MOSDAC products are not fabricated when their required datasets/models are absent.

The current What-If engine therefore performs a transparent rainfall-hazard sensitivity experiment. Temperature and sea-level parameters are recorded but explicitly marked as uncoupled until validated physical/data models are connected.

## Research

The implementation rationale and architecture are documented in `docs/DIGITAL_TWIN_RESEARCH.md`.

Primary references include NIST Digital Twins, NASA Earth System Digital Twins and Destination Earth Digital Twins.

## Local development

```bash
# backend
python -m uvicorn backend.api.main:app --reload --port 8000

# frontend, in another terminal
npm run dev

# frontend + backend CI checks
npm run build
python -m compileall backend scripts
```

## Production architecture

- GitHub: source control and reproducible project history
- Vercel: Next.js frontend
- Render: FastAPI scientific backend
- External/object storage: large climate datasets and the 28+ GB Prithvi-WxC checkpoint
- MapLibre: geospatial visualization
- Xarray/NumPy: scientific data processing
- IMD/ERA5/Sentinel-2/Prithvi-EO: current connected data/model layers
