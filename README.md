# India Climate Digital Twin

An AI-ready geospatial climate intelligence platform for India. The repository is being developed as **Bharat Climate Twin**: an API-first, provenance-aware digital-twin platform combining observations, forecasts, impact models, assets, scenarios and decision support.

## Digital-twin architecture

The implementation follows the Earth-system pattern of a continuously updated digital replica plus forecasting and impact assessment. NASA describes these as interconnected components for monitoring, forecasting and actionable decision support.

**Observed Earth system -> validation/QC -> synchronized digital state -> forecasting + impact models -> What Now / What Next / What If -> decision support**

The twin is not a static map and not merely an AI model. Every operational result is intended to carry provenance, timestamps, model/version metadata, uncertainty or coverage information and explicit limitations.

## Current implementation

- Next.js + React frontend with MapLibre-based map UI
- FastAPI + Xarray scientific backend
- IMD rainfall NetCDF ingestion, statistics, grids and GeoJSON
- Extreme rainfall classification and spatial event layers
- Rainfall hazard-risk scoring and validation
- Chennai Sentinel-2 historical archive and validated Prithvi-EO input pipeline
- Chennai Prithvi-EO + ERA5 fused feature matrix
- Deterministic observation-derived Digital Twin State with provenance and state hash
- Climate Twin Engine with What Now, What Next and What If workflows
- Prithvi-WxC official-runtime integration boundary with strict MERRA-2/model gating
- Industry risk contract and auditable asset-risk engine
- Canonical asset, exposure, scenario and alert domain models
- PostGIS spatial persistence schema for assets, locations, datasets, model registry, risk assessments, scenarios and audit events
- STAC-oriented dataset catalog contract for large geospatial data
- Multilingual early-warning message contract covering English plus major Indian-language locales
- HEC-RAS-compatible flood/hydraulic integration boundary; no fabricated flood depth
- Versioned `/api/v1` industry-platform APIs
- GitHub Actions CI for frontend build, backend compilation/import checks and tests

## Digital Twin API

| Capability | Endpoint |
|---|---|
| Twin health | `/api/twin/health` |
| What Now | `/api/twin/now` |
| What Next | `/api/twin/next?horizon=7` |
| What If | `/api/twin/what-if?...` |
| Twin vector | `/api/twin/state` |
| Risk contract | `/api/risk/contract` |
| Industry capabilities | `/api/v1/platform/capabilities` |
| Asset create/update | `POST /api/v1/assets` |
| Asset lookup | `GET /api/v1/assets/{asset_id}` |
| Asset risk | `POST /api/v1/assets/{asset_id}/risk` |
| Scenario creation | `POST /api/v1/scenarios` |
| Dataset catalog contract | `/api/v1/catalog/contract` |
| Flood twin status | `/api/v1/flood/status` |
| Alert language catalog | `/api/v1/alerts/languages` |
| Alert preview | `POST /api/v1/alerts/preview` |
| Prithvi status | `/api/ai/prithvi/status` |
| Prithvi forecast | `POST /api/ai/prithvi/forecast` |
| Validation | `/api/validation` |
| Provenance | `/api/provenance` |

## Industry data architecture

The platform stores transactional spatial data and metadata in **PostgreSQL/PostGIS**. Large multidimensional climate arrays and satellite products remain external to the transactional database and are referenced through a STAC-compatible catalog.

```text
Sensors / IMD / Reanalysis / Satellites / NWP / Private data
                         |
                         v
              Ingestion + QC + lineage
                         |
              +----------+----------+
              |                     |
              v                     v
       Object storage             PostGIS
       COG / Zarr / NetCDF        assets / vectors / metadata
              |                     |
              +----------+----------+
                         v
                   Twin state
                         |
            +------------+-------------+
            |            |              |
        Forecasts      Hazards       Scenarios
            |            |              |
            +------------+--------------+
                         v
                 Risk / Exposure
                         |
               Alerts / Reports / GIS
```

The repository includes `database/migrations/001_industry_core.sql` and a local PostGIS service under `infra/docker-compose.yml`.

## Scientific guardrails

- Missing variables remain unavailable; they are never filled with fabricated values.
- A screening score is not presented as a calibrated probability.
- A generic risk score is not a substitute for a validated flood, heat, agriculture or coastal physical model.
- Prithvi-WxC is enabled only when its documented input/runtime contract is satisfied.
- Flood depth/inundation is not generated until a validated hydraulic model and required terrain/boundary data are connected.
- Long-term 2030/2050/2100 scenarios require validated climate projection datasets and are not implied by simple perturbations.
- Large model weights and climate archives are external dependencies; normal API requests must not download multi-GB assets.

## Production roadmap

### Phase 1 — platform foundation

- PostGIS asset/location persistence
- STAC data catalog
- provenance and audit events
- IAM/SSO/RBAC boundary
- observability and request tracing

### Phase 2 — metropolitan pilot

- validated DEM and drainage data
- rainfall-runoff model
- HEC-RAS 2D hydraulic model
- urban heat model
- population/infrastructure exposure
- asset-level flood/heat risk
- multilingual alert delivery

### Phase 3 — national scale

- river-basin and coastal twins
- agriculture and water twins
- enterprise portfolio risk
- 2030/2050/2100 climate projections
- financial loss and adaptation models
- Kafka/event streaming
- Kubernetes/Terraform/Helm deployment
- OGC-compatible geospatial services

## Local development

```bash
# backend
python -m uvicorn backend.api.main:app --reload --port 8000

# frontend, in another terminal
npm run dev

# CI-equivalent backend checks
python -m compileall backend scripts
python -m unittest discover -s backend/tests -p 'test_*.py' -v

# optional local PostGIS
cd infra && docker compose up -d
```

## Production architecture

- GitHub: source control and reproducible history
- FastAPI: scientific/API services
- PostgreSQL/PostGIS: transactional geospatial system of record
- STAC + object storage: large Earth-observation/climate data plane
- COG/Zarr/NetCDF: cloud-native scientific data formats
- MapLibre/Cesium: 2D/3D visualization
- Xarray/NumPy: scientific processing
- IMD/MERRA-2/ERA5/Indian EO: observation and atmospheric context
- Prithvi-WxC: gated AI forecasting component
- HEC-RAS or another validated hydraulic solver: flood component

## Standards and research basis

The geospatial data architecture is designed around interoperable OGC concepts including STAC, OGC API - Features and Cloud Optimized GeoTIFF. The digital-twin architecture follows Earth-system digital-twin principles rather than treating visualization as the twin itself.
