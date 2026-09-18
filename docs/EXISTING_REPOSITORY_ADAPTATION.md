# Existing Repository Adaptation

## Baseline analysis

The repository already contains the working India Climate Digital Twin application. The existing frontend is Next.js 16 + React 19 + MapLibre GL, not CesiumJS. The backend is FastAPI with a rainfall/twin/risk service layer. The project therefore keeps the existing MapLibre geospatial foundation rather than introducing a second 3D engine.

### Reused foundations

- Next.js application shell and console layout
- MapLibre map initialization, navigation, India center and state GeoJSON
- Existing rainfall, extreme-event and risk GeoJSON services
- Existing state hierarchy and state-twin services
- FastAPI routing and service abstraction
- Existing risk, scenario, provenance and validation services
- Existing PostGIS-oriented industry platform layer
- Existing STAC-oriented dataset catalog
- Existing Prithvi-WxC integration boundary
- Existing CI/build/deployment configuration

### Climate transformation

The console now exposes a stable climate-layer contract for:

- Rainfall
- Temperature
- Land Surface Temperature (LST)
- Sea Surface Temperature (SST)
- Climate anomalies
- Climate risk
- Climate events

Only provider-backed layers are reported as available. Temperature, LST and SST return explicit NO_DATA/provider-required responses until validated source adapters are connected.

### Administrative exploration

India remains the default map extent. State selection is preserved. A district exploration API contract is available without inventing district data.

### Geospatial data plane

The backend now exposes lightweight OGC-aligned discovery/query building blocks under /ogc and a STAC-compatible catalog boundary. These are implementation building blocks, not formal conformance claims. The design follows current OGC STAC and OGC API Features patterns. Large climate assets remain external to the browser and repository.

### Scientific guardrail

No new climate values or forecasts are fabricated. The existing IMD rainfall path remains the connected observation/forecast baseline; other climate variables are explicit provider integration points until real datasets are connected.
