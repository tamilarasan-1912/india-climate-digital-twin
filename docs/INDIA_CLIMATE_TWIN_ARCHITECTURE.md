# India Climate Digital Twin — Target Architecture

## 1. Scope

The physical counterpart is **India's climate/weather/environmental state**, represented at national and progressively finer administrative/spatial levels. The project is not an Earth-system Digital Twin of the whole planet.

International programmes such as NIST Digital Twin research and Destination Earth are architectural/scientific references. Their global scope and supercomputing infrastructure are not assumed to exist in this project.

## 2. Digital Twin lifecycle

```text
REAL-WORLD INDIA
   │
   ├── weather observations
   ├── satellite / EO observations
   ├── reanalysis
   ├── authoritative forecast/event products
   └── environmental observations
   │
   ▼
INGESTION
   │
   ▼
QUALITY CONTROL / NORMALIZATION
   │
   ├── schema validation
   ├── spatial alignment
   ├── temporal alignment
   ├── missing/stale-data detection
   └── provenance
   │
   ▼
INDIA DIGITAL TWIN STATE
   │
   ├── location/grid
   ├── timestamp
   ├── variable
   ├── observed / estimated / forecast value
   ├── uncertainty / confidence when available
   ├── source / model
   └── freshness
   │
   ├───────────────┬────────────────┬─────────────────┐
   ▼               ▼                ▼                 ▼
STATE ESTIMATION  FORECASTING     EXTREMES       SCENARIOS
   │               │                │                 │
   └───────────────┴────────────────┴─────────────────┘
                           │
                           ▼
                    RISK / IMPACT LAYER
                           │
                           ▼
                     TWIN API LAYER
                           │
                           ▼
                MAP / CHARTS / DECISION UI
                           │
                           ▼
                    USER FEEDBACK / USE
                           │
                           └──────► next synchronization cycle
```

## 3. Current implementation mapped to the architecture

### Acquisition

- IMD RF25 gridded rainfall is the currently connected national observation dataset.
- Sentinel-2 historical data and Prithvi-EO preparation exist for a Chennai research subset.
- ERA5/Prithvi-EO fused features exist for the Chennai research subset.
- MERRA-2/Prithvi-WxC is represented by a strict input contract; it is not bypassed with synthetic atmospheric variables.

### Data engineering

The backend uses Xarray/NumPy/pandas/raster/geospatial processing and exposes explicit validation/provenance endpoints. The next production evolution should move repeated file processing into scheduled ingestion jobs and a persistent metadata/catalog layer.

### Digital Twin state

`backend/services/twin_engine.py` builds an observation-derived national state from the selected IMD date and rainfall-risk field. It includes a deterministic state hash, observation date, source metadata, rolling/anomaly features, risk distribution and coverage.

State-level APIs use the India administrative hierarchy and must return `NO DATA` rather than infer state values from national aggregates when a validated state aggregation is unavailable.

### Forecasting

The current baseline is a 7-day moving-average rainfall forecast with walk-forward evaluation. It is intentionally simple and reproducible. Prithvi-WxC is the planned advanced weather/climate model, but only valid 160-variable MERRA-2 inputs can activate it.

### Extreme events

The currently operational event logic is precipitation-threshold based. Heatwave, drought, flood and cyclone capabilities must only be activated after their required datasets and validated methods are connected.

### Scenarios

The existing What-If engine is a rainfall-hazard sensitivity experiment. It is not presented as a full physical multi-hazard impact model.

### Visualization

Next.js/React + MapLibre provide the operational UI. The UI should expose the distinction between observed, forecast and hypothetical states, together with source/model/freshness information.

## 4. State record contract

Conceptually, each twin observation/state record should support:

```text
location_id
latitude
longitude
administrative_level
administrative_id
timestamp
variable
observed_value
estimated_value
forecast_value
unit
anomaly
uncertainty
confidence
source
model
last_updated
quality_flag
provenance_id
```

Not every source currently supplies every field. Missing fields must remain explicit rather than being filled with fabricated values.

## 5. Why this architecture is a Digital Twin core

The important distinction is the relationship between the real-world counterpart and the digital state. The system does not merely display a static map or run an isolated forecast. A selected observation state is materialized into a reproducible twin state, that state is passed to downstream prediction/risk/scenario services, and the representation can be regenerated when the source state changes.

The current implementation is therefore best described as an **auditable India Climate Digital Twin core**, with several capabilities still gated by data/model availability.

## 6. Model strategy

Use the least complex validated model that answers the use case:

1. Statistical baseline — benchmark and regression guardrail.
2. Tree/time-series ML — only when sufficient features and temporal history exist.
3. Spatial-temporal deep learning — for problems with enough gridded history.
4. Prithvi-WxC — advanced multi-variable weather/climate forecasting once its official input contract is satisfied.
5. Prithvi-EO — satellite representation/EO downstream tasks.
6. Authoritative external products — for operational event information when building an independent physical forecast is not scientifically justified.

Every model output should carry model identity, forecast origin, horizon, data timestamp and uncertainty/calibration status.

## 7. Validation strategy

For forecasting, use temporal/rolling evaluation rather than random shuffling. Report task-appropriate metrics such as MAE, RMSE and bias for continuous rainfall forecasts, and precision/recall/F1/PR-AUC plus calibration measures for event prediction where enough labelled events exist.

For spatial products, validate geometry, coverage, units, threshold logic and point-to-feature consistency before exposing them to the UI.

## 8. Operational resilience

The data layer should distinguish:

- fresh and synchronized;
- stale but available;
- source unavailable;
- partially available;
- invalid;
- planned/not connected.

Retries, caching, rate limits and external credentials belong at provider boundaries. Secrets must be environment variables and never committed.

## 9. Research basis

- NIST, Digital Twins: https://www.nist.gov/digital-twins
- NIST, Essential Elements: https://www.nist.gov/digital-twins/essential-elements
- NIST IR 8356: https://csrc.nist.gov/pubs/ir/8356/final
- NIST Digital Twin Core Conceptual Models and Services: https://www.nist.gov/publications/digital-twin-core-conceptual-models-and-services
- ECMWF, Weather-Induced Extremes Digital Twin: https://www.ecmwf.int/en/forecasts/datasets/weather-induced-extremes-digital-twin-extremes-dt
- ECMWF, Destination Earth Climate Adaptation Digital Twin: https://www.ecmwf.int/en/forecasts/dataset/destination-earth-digital-twin-climate-change-adaptation
- MOSDAC / ISRO: https://mosdac.gov.in/
