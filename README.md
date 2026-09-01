# India Climate Digital Twin

An AI-ready geospatial climate intelligence platform for India. The current scientific core is built around validated IMD gridded rainfall, Chennai ERA5 + Prithvi-EO fused features, a deterministic 128-D twin-state representation, extreme-rainfall detection, and a rainfall hazard-risk engine.

## Current implementation

- Next.js + React frontend with MapLibre-based map UI
- FastAPI + Xarray scientific backend
- IMD rainfall NetCDF ingestion, statistics, grids and GeoJSON
- Extreme rainfall classification and spatial event layers
- Rainfall hazard-risk scoring and validation
- Chennai Sentinel-2 historical archive and validated Prithvi-EO input pipeline
- Chennai Prithvi-EO + ERA5 fused feature matrix
- 128-D deterministic Digital Twin State
- 7-day moving-average rainfall baseline with walk-forward MAE/RMSE/Bias
- Operational APIs for twin state, historical analytics, baseline forecast, scenarios, explainability, provenance and validation
- `/operations` control-room page for the new operational functions
- GitHub Actions CI for frontend build and backend import/compile checks

## Operational API

| Capability | Endpoint |
|---|---|
| Health | `/api/health` |
| Climate variables | `/api/climate/variables` |
| Rainfall | `/api/rainfall/*` |
| Extreme events | `/api/extreme-events/*` |
| Risk | `/api/risk/*` |
| Twin state | `/api/twin/*` |
| Historical | `/api/historical/rainfall` |
| Baseline forecast | `/api/forecast/baseline` |
| Model registry | `/api/models` |
| Explainability | `/api/explain/rainfall` |
| What-if sensitivity | `/api/scenarios/simulate` |
| Validation | `/api/validation` |
| Provenance | `/api/provenance` |

## Important scientific limitation

Prithvi-WxC is **not** presented as operational until compatible multi-variable atmospheric input is available. The current rainfall-only IMD dataset is not a valid substitute for that model's atmospheric input contract. Likewise, temperature, population exposure, flood physics, sea-level impacts and MOSDAC products are not fabricated when their required datasets are absent.

The scenario endpoint is therefore a transparent rainfall-hazard sensitivity experiment, not a physical flood or climate-impact forecast.

## Local development

```bash
# backend
python -m uvicorn backend.api.main:app --reload --port 8000

# frontend, in another terminal
npm run dev

# API smoke test
python scripts/smoke_test_api.py
```
