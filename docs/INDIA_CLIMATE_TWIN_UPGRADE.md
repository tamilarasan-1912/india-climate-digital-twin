# India Climate Digital Twin — Multi-Variable Upgrade

## Purpose

This document defines the implementation path from the current rainfall-centric digital-twin core to a scientifically defensible, multi-variable India Climate Digital Twin.

The existing repository already implements the core digital-twin lifecycle:

`observations -> validation/QC -> synchronized state -> forecast/risk -> What Now / What Next / What If -> decision support`

The upgrade must preserve that architecture rather than replacing the twin with a single AI model.

## 1. Target architecture

```text
IMD / ERA5 / MERRA-2 / Indian EO / other validated sources
                         |
                         v
              ingestion + temporal alignment
                         |
                         v
             quality control + provenance
                         |
                         v
               common geospatial grid
                         |
                         v
              DIGITAL TWIN STATE STORE
                         |
          +--------------+---------------+
          |              |               |
          v              v               v
      What Now       What Next        What If
          |              |               |
          |        AI/NWP/ML models      |
          |              |               |
          +--------------+---------------+
                         |
                         v
                 impact/risk models
                         |
        +----------------+----------------+
        |                |                |
        v                v                v
      flood            heat             drought
        |                |                |
        +----------------+----------------+
                         |
                         v
                decision-support UI
```

The twin state is the synchronized representation. Forecast and impact models are components operating on that state.

## 2. State variables

The current deterministic rainfall state remains supported. The target state schema is extensible and should contain only variables for which validated data exists.

### Core atmospheric variables

- precipitation
- 2 m air temperature
- relative humidity / dew point where available
- surface pressure
- 10 m wind components
- geopotential/upper-air variables when supplied by the forecast model

### Land and Earth-observation variables

- soil moisture where a validated source is connected
- vegetation/NDVI or equivalent EO indicators
- land-surface temperature where available
- snow/ice indicators where relevant
- surface reflectance-derived features where relevant

### Derived climate indicators

- rainfall anomaly
- temperature anomaly
- standardized precipitation indicators when sufficient history exists
- rolling precipitation/temperature statistics
- extreme-event indicators
- hazard scores
- uncertainty/coverage metadata

No variable may be populated with a fabricated default merely to satisfy a model contract.

## 3. Data contracts

Every connected dataset must declare:

- provider and dataset identifier
- variable names and units
- spatial CRS/grid and resolution
- temporal resolution and timestamp convention
- geographic coverage
- valid range / missing-value convention
- preprocessing and regridding method
- retrieval/update timestamp
- license/usage metadata where available
- provenance identifier or content hash when practical

The twin state must retain source provenance so a state can be reproduced or audited.

## 4. Prithvi-WxC integration policy

Prithvi-WxC is an optional forecasting component, not the definition of the twin.

The repository currently gates inference behind a validated MERRA-2 contract. Keep this gate. The production integration must:

1. acquire compatible MERRA-2 atmospheric fields;
2. validate the expected variable count, timestamps and six-hour interval;
3. normalize/regrid exactly as required by the model implementation;
4. construct the model tensor through a reproducible adapter/dataloader;
5. execute the model only after contract validation succeeds;
6. record model version, checkpoint identifier and preprocessing version;
7. transform model output into the twin's common grid/variable schema;
8. attach uncertainty and data-coverage metadata where available;
9. expose forecast output through the existing `/api/twin/next` pathway only after validation.

The current fallback moving-average forecast remains a benchmark, not a replacement for Prithvi-WxC.

## 5. India-specific fusion strategy

Use source-specific strengths instead of blindly averaging datasets.

- IMD: authoritative India rainfall observations/grids where available.
- ERA5/MERRA-2: physically consistent atmospheric/reanalysis context.
- Indian satellite/EO sources: high-frequency or spatially rich observations where validated.
- Sentinel/Prithvi-EO: land-surface and Earth-observation feature generation where relevant.

Fusion should be explicit. Each fused variable must identify which sources contributed and how they were harmonized.

## 6. What Now

`What Now` is a synchronized snapshot of the latest valid observation/reanalysis state.

It should provide:

- variable values;
- spatial maps;
- anomalies;
- detected extremes;
- hazard/risk fields;
- data freshness;
- coverage;
- confidence/uncertainty;
- provenance;
- deterministic state hash.

## 7. What Next

Forecasting should support model selection and comparison rather than hiding the model behind a single number.

Required metadata:

- forecast origin;
- horizon;
- model name/version;
- input state hash;
- forecast variables;
- units;
- lead time;
- validation metrics;
- uncertainty/calibration status;
- whether future observations were used.

The current 7-day moving-average baseline remains the benchmark for regression testing.

## 8. What If

Scenarios must distinguish between mathematical sensitivity experiments and physical simulations.

Examples:

- precipitation perturbation -> rainfall hazard sensitivity;
- temperature perturbation -> heat-risk sensitivity only when a validated temperature/risk model is connected;
- sea-level perturbation -> coastal inundation only after a validated elevation/coastal model is connected.

The API must explicitly report which parameters are coupled and which are currently uncoupled.

## 9. Multi-hazard impact layer

Add impact models incrementally:

1. rainfall hazard — existing;
2. heat stress — temperature + humidity + exposure data;
3. drought — precipitation/soil-moisture/evapotranspiration indicators;
4. flood — rainfall + terrain + drainage/hydrology model;
5. agriculture — weather/soil/crop-stage model;
6. coastal risk — sea level + surge + elevation/coastal model.

A risk score is not equivalent to a physical impact model. Each impact engine must document its assumptions, training/validation data and limitations.

## 10. Validation

Every forecast/impact model must be evaluated using time-respecting validation.

Minimum metrics where applicable:

- MAE
- RMSE
- bias
- correlation
- event detection precision/recall/F1
- calibration / reliability for probabilistic forecasts
- spatial skill metrics for gridded forecasts

Historical extreme events should be retained as regression cases so future changes cannot silently degrade event detection.

## 11. Engineering requirements

- Keep scientific computation in the FastAPI/backend layer.
- Keep the frontend presentation layer independent from dataset-specific logic.
- Prefer typed contracts and explicit units.
- Cache expensive geospatial masks and model metadata.
- Never download a multi-GB checkpoint during a normal web request.
- Treat large models/datasets as external/object-storage dependencies.
- Keep CI checks for imports, type/compile correctness and frontend build.
- Add API tests for state reproducibility, invalid data contracts and model gating.

## 12. Definition of done

The project can claim a multi-variable India Climate Digital Twin only when:

- at least one validated atmospheric source beyond rainfall is connected;
- the synchronized state contains multiple independently sourced variables;
- provenance is attached to every state;
- at least one validated forecast model consumes the synchronized state or its documented compatible representation;
- forecast outputs are validated against historical data;
- What-If parameters are physically coupled where claimed;
- uncertainty/coverage is visible to users;
- unavailable variables remain explicitly unavailable;
- the UI exposes What Now, What Next, What If, risk and scientific provenance as separate workflows.

Until then, describe the implementation as an operational digital-twin core and state exactly which variables/models are active.

## Research basis

The architecture follows the Earth-system digital-twin concepts documented by NIST, NASA Earth System Digital Twin work and Destination Earth. The repository's existing `docs/DIGITAL_TWIN_RESEARCH.md` contains the project's source list and rationale.
