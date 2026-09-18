# Existing Repository Adaptation Analysis

## Baseline
Repository: `tamilarasan-1912/india-climate-digital-twin`

The existing application is already an adaptation of the former generic geospatial/dashboard foundation; this work preserves that structure rather than rebuilding it.

## Existing stack
- **Frontend:** Next.js + TypeScript + Tailwind CSS.
- **Map:** MapLibre GL JS. The repository does **not** currently use CesiumJS; therefore the existing MapLibre implementation is preserved rather than introducing a second globe framework.
- **Geospatial view:** `src/app/components/ClimateMap.tsx`, centered on India, with India state GeoJSON, terrain raster-DEM, navigation, state selection, rainfall/event/risk overlays.
- **Primary UI:** `src/app/console/page.tsx` and existing console styling/layout.
- **Backend:** FastAPI under `backend/api`, with service modules for rainfall, extreme events, risk, twin state, forecasting, provenance, Prithvi, scenarios and platform APIs.
- **Data contracts:** climate variable contract, multi-variable twin contract, risk contract, dataset/STAC-oriented metadata, OGC-aligned routes.
- **Storage:** PostGIS migration and repository layer exist for industry/twin metadata; large scientific data is kept outside browser responses.
- **Model layer:** Prithvi-WxC integration boundary, MERRA-2 validation/tensor preparation and baseline forecast service.
- **Deployment:** Vercel frontend + Render FastAPI configuration; CI is defined in GitHub Actions.
- **Configuration:** `.env.example` contains the public API URL; secrets are excluded by `.gitignore`.

## Existing data flow
Provider/dataset -> ingestion/validation services -> climate/twin contracts -> FastAPI -> console -> MapLibre visualization.

Rainfall is currently the only connected visual climate layer. Temperature, LST, SST and anomalies intentionally report provider-required/NO_DATA states instead of fabricated values.

## Reuse decision
Preserved: map component, India state geometry, terrain, navigation, console cards/metrics, climate/risk/twin services, OGC/STAC contracts, FastAPI conventions, deployment and CI.

Added in this adaptation pass: a configurable provider registry for non-rainfall climate layers and an explicit configuration surface for external climate-data endpoints. No large datasets or credentials are added.
