# Final implementation status

Updated: 2026-09-23

This status is deliberately capability-based. `IMPLEMENTED` means code and a
contract exist; `CONNECTED` means the repository has a validated source and can
serve data; `BLOCKED` means a real external dataset, model, credential or
runtime is still required. A blocked capability is never represented as a
synthetic value.

## Connected and validated

| Capability | Status | Evidence and limits |
|---|---|---|
| India-scoped FastAPI platform | CONNECTED | FastAPI routes, request IDs, structured errors, security headers and restricted CORS |
| Next.js console | CONNECTED | Next.js/TypeScript app with same-origin API rewrites |
| LAN development and HMR | VALIDATED | `0.0.0.0` binding, automatic LAN origin detection and tested `/_next/hmr` WebSocket |
| MapLibre visualization | CONNECTED | Persistent map instance, state boundaries, terrain, IMD rainfall raster tiles and GeoJSON overlays |
| IMD RF25 rainfall observation | CONNECTED / VALIDATED | `backend/data/RF25_ind2024_rfp25.nc`; daily 2024 coverage, 0.25-degree grid |
| Rainfall statistics and grids | CONNECTED / VALIDATED | Real NetCDF values only; invalid dates and missing datasets return explicit errors/status |
| State rainfall aggregation | CONNECTED / VALIDATED | Real state polygons and IMD grid-cell-centre spatial aggregation |
| Rainfall hazard screening | CONNECTED / VALIDATED | Rainfall-only thresholds; not flood depth, probability or multi-hazard impact |
| Extreme rainfall events | CONNECTED / VALIDATED | IMD-derived thresholds and GeoJSON event points |
| Baseline forecast | CONNECTED / PARTIAL | Seven-day moving-average `BASELINE FORECAST`; not AI and not a calibrated NWP forecast |
| What-If rainfall sensitivity | CONNECTED / PARTIAL | Rainfall hazard perturbation; temperature/sea-level inputs are explicitly uncoupled |
| Provenance and validation contracts | CONNECTED | Dataset/source/model/status metadata on implemented outputs |
| Provider runtime validation | IMPLEMENTED | Rejects malformed, unitless, untimestamped, unspatial or variable-less provider payloads |
| Security/operator boundary | PARTIAL | Operator and rate-limit boundaries exist; production IAM/SSO/RBAC remains external |

## Blocked or provider-required

| Capability | Status | Required dependency |
|---|---|---|
| ADM1/ADM2 district drill-down | BLOCKED in this checkout | Real validated `IND-ADM1.geojson` and `IND-ADM2.geojson` geoBoundaries cache, or an approved authoritative replacement |
| Temperature | PROVIDER REQUIRED | Validated IMD/ERA5 adapter and data response |
| Land-surface temperature | PROVIDER REQUIRED | Validated MOSDAC/MODIS/Landsat adapter and data response |
| Sea-surface temperature | PROVIDER REQUIRED | Validated INCOIS/MOSDAC/ERA5 adapter and data response |
| Climate anomalies | PARTIAL / PROVIDER REQUIRED | Observation plus validated climatology source |
| Prithvi-WxC forecast | BLOCKED | Official 160-variable, two-timestep MERRA-2 input, normalization assets, checkpoint and compatible compute |
| Flood physics | BLOCKED | DEM, drainage, rainfall-runoff and hydraulic model |
| Drought, cyclone, coastal and sectoral impacts | NOT OPERATIONAL | Validated source/model pipelines |
| City and asset-level twin | NOT OPERATIONAL | Independently validated city boundaries, asset registry, exposure and vulnerability data |
| Continuous ingestion/scheduling | NOT OPERATIONAL | Production scheduler, object storage, monitoring and provider credentials |
| Calibrated uncertainty/probabilistic validation | PARTIAL | Baseline rainfall metrics exist; calibrated multi-variable uncertainty does not |

## Administrative geometry policy

The runtime uses geoBoundaries ADM1/ADM2 and never substitutes state polygons,
centroids, grids or fabricated shapes for districts. Geometry is resolved in
this order:

1. A valid cache file in `backend/data/admin_cache/`.
2. An externally mounted directory from `ADMIN_BOUNDARY_CACHE_DIR`.
3. A provider download when runtime egress is available.
4. HTTP `503` / `NO_DATA` if none is available.

The cache directory is gitignored by design. It must be provisioned with real,
validated geometry; this repository does not commit a generated or synthetic
boundary dataset. `GET /api/system/status` reports `PROVIDER REQUIRED` when the
cache is absent without performing a slow network probe.

## Scientific labeling policy

- `OBSERVATION`: connected IMD rainfall values.
- `BASELINE FORECAST`: moving-average extrapolation only.
- `SCENARIO` / `SENSITIVITY EXPERIMENT`: perturbation outputs, never predictions.
- `MODEL OUTPUT`: only when a declared model and validated input/output are present.
- `NO_DATA` / `provider_required` / `BLOCKED`: unavailable scientific layers.

## Verification performed

Passing checks:

- `python -m compileall -q backend scripts`
- `npx tsc --noEmit`
- `npm run lint`
- `npm run build`
- targeted intelligence/capability tests
- administrative-boundary resilience tests
- scientific null-handling regression tests
- live uvicorn health/proxy smoke tests
- localhost and LAN Next.js page requests
- localhost/LAN HMR WebSocket handshake

On this fresh checkout, the complete backend discovery suite has `84` passing
tests and `12` district-geometry failures/errors because the ignored validated
ADM1/ADM2 cache is absent and provider egress is unavailable. Those requests
correctly remain unavailable rather than being made to pass with fabricated
geometry. The remaining failures are therefore an explicit provisioning gate,
not a scientific fallback.
