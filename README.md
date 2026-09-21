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
- State-level rainfall aggregation over real IMD grid cells covered by real state polygons
- District-level rainfall aggregation over real IMD grid cells covered by real geoBoundaries ADM2 polygons
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
| State climate aggregation | `/api/india/state/{state_id}/climate/{date}` |
| All-state climate aggregation | `/api/india/states/climate/{date}` |
| State district rollup | `/api/india/state/{state_id}/districts/climate/{date}` |
| National district aggregation | `/api/india/districts/climate/{date}` |
| Single district aggregation | `/api/india/district/{district_id}/climate/{date}` |
| District geometry coverage | `/api/india/districts/coverage` |
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

## Implementation status matrix

Completion model: `IMPLEMENTED` (code exists) → `CONNECTED` (real data flows)
→ `VALIDATED` (tested against real data) → `PRODUCTION_READY`.

| Area | Implemented | Connected | Validated | Notes |
|---|---|---|---|---|
| IMD rainfall | Yes | Yes | Yes | `RF25_ind2024_rfp25.nc`, 366 days, 129×135 grid |
| State aggregation | Yes | Yes | Yes | 34/36 states; 2 island UTs have no grid centre |
| District aggregation | Yes | Yes | Yes | 702/735 districts; 33 report `no_grid_coverage` |
| Rainfall risk | Yes | Yes | Yes | Rainfall-only hazard screening |
| Extreme events | Yes | Yes | Yes | IMD-derived rainfall thresholds |
| Forecasting | Yes | Yes | Partial | 7-day moving-average baseline; not AI-calibrated |
| Temperature | Yes | No | No | `PROVIDER REQUIRED` — adapter ready, no endpoint |
| LST / SST | Yes | No | No | `PROVIDER REQUIRED` |
| Anomalies | Yes | No | No | Requires validated climatology + observation |
| Prithvi-WxC | Yes | No | Blocked | Checkpoint, PyTorch, scalers, MERRA-2 absent |
| Flood twin | Yes | No | Blocked | No validated hydraulic solver |
| Heat risk | Yes | Partial | Screening | Needs validated heat-health model |
| Drought | Contract only | No | No | Requires validated SPI/soil-moisture source |
| Cyclone | Contract only | No | No | Requires official track/intensity source |
| Alerts | Yes | Partial | Yes | 12 languages; generation ≠ operational issuance |
| Provenance | Yes | Yes | Yes | Attached to every observation |
| Validation | Yes | Partial | Yes | Baseline metrics only |

District aggregation is a genuine spatial operation: IMD 0.25° grid-point
centres are intersected with geoBoundaries ADM2 polygons using an STRtree, and
mean/min/max/median/risk are computed only over intersecting cells. A district
whose polygon contains no grid-point centre reports
`status: no_grid_coverage` with `null` metrics — never a parent-state or
neighbouring value. District maxima are cross-checked against state polygons in
`test_district_climate_service.py` and can never exceed the state maximum.

## Status and capability reporting

`/api/system/status` returns a per-capability contract used by the System console
page. Each capability reports a state derived from observed data or model
availability — never from the presence of an environment variable:

```text
CONNECTED · AVAILABLE · DEGRADED · NO DATA · PROVIDER REQUIRED · BLOCKED · VALIDATION REQUIRED
```

A provider URL that is set but unvalidated is reported as
`CONFIGURED (VALIDATION PENDING)`. `/api/v1/security/status` reports the
administrative boundary truthfully as `enforced` or `disabled_development_mode`.

## Terminology policy

Scientific labelling is enforced in the API and the UI:

| What it is | What it is called |
|---|---|
| 7-day moving average extrapolation | `BASELINE FORECAST` — not an AI weather model |
| Mathematical perturbation of a layer | `SENSITIVITY EXPERIMENT` / `coupling-aware sensitivity analysis` — not a climate prediction |
| Deterministic projection/SVD of fused features | `deterministic climate-state representation` — not a trained neural latent |
| Unvalidated provider response | `NO_DATA` with `provider_required: true` |
| Generated alert text | `message_generation` — distinct from `alert_issuance` |

## Environment variables

Every variable is documented in `.env.example`. Configuration alone never makes
a provider `CONNECTED`.

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL used by the Next.js rewrites |
| `CORS_ALLOWED_ORIGINS` | Comma-separated browser origins allowed to call the API |
| `CLIMATE_PROVIDER_TEMPERATURE_URL` | Optional validated temperature provider endpoint |
| `CLIMATE_PROVIDER_LST_URL` | Optional validated land-surface-temperature provider |
| `CLIMATE_PROVIDER_SST_URL` | Optional validated sea-surface-temperature provider |
| `CLIMATE_PROVIDER_ANOMALIES_URL` | Optional validated anomaly provider |
| `CLIMATE_PROVIDER_TIMEOUT_SECONDS` | Per-request provider timeout |
| `ADMIN_API_KEY` | Operator key for administrative/write APIs; unset disables the boundary |
| `RATE_LIMIT_PER_MINUTE` | Process-local per-client request limit |
| `TRUST_PROXY_HEADERS` | Honour `X-Forwarded-For` only behind a trusted reverse proxy |
| `ADMIN_BOUNDARY_CACHE_TTL` | Boundary cache lifetime in seconds |
| `CLIMATE_CATALOG_ROOT` | Local STAC-compatible catalog index directory |

Never commit real secrets. `.env` is not tracked.

## Testing

```bash
# full backend suite (CI-equivalent)
python -m compileall backend scripts
python -m unittest discover -s backend/tests -p 'test_*.py' -v

# frontend
npm ci
npm run lint
npx tsc --noEmit
npm run build
```

Tests cover the IMD rainfall contract, dataset lifecycle, provider adapters,
catalog registration/search/lineage, rate limiting, the operator boundary,
route-module integrity and the no-fabrication policy. Provider tests run against
in-process HTTP fixtures, so CI never depends on an external climate provider.

## Database

PostGIS is optional. The application degrades gracefully: without
`DATABASE_URL`, asset persistence returns **503** with an explicit
"dataset, provider or model is unavailable" message instead of substituting an
in-memory fake production store. Public read APIs remain fully available.
Bring up the local stack with `cd infra && docker compose up -d`.

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

### Full stack in Docker

`Dockerfile`, `backend/Dockerfile` and the root `docker-compose.yml` run the
frontend and API together without installing Python or Node locally:

```bash
docker compose up --build
# frontend -> http://localhost:3000
# backend  -> http://localhost:8000/api/health
```

Large and licensed data (the IMD NetCDF file and administrative geometry) is
mounted read-only rather than baked into the image, and the writable
administrative-boundary cache is pointed at its own volume via
`ADMIN_BOUNDARY_CACHE_DIR`. If the geoBoundaries upstream is unreachable, a
populated cache is still served (see `docs/ADMINISTRATIVE_DATA_SOURCE.md`).
This is a local development environment; production remains Vercel + Render.

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
