# Digital Twin Research and Implementation Basis

## 1. Research conclusion

A Digital Twin is more than a dashboard, GIS, simulation or ML predictor. NIST defines a Digital Twin as a virtual representation of a real-world entity and its current guidance emphasizes dynamic connection/synchronization, state representation, prediction, simulation and decision support. NIST also notes that Digital Twins expose states and transitions between states and require trust/security considerations.

For this repository, the represented entity is **India's climate/weather/environmental state**. The system boundary is India; global Earth-system programmes are references rather than the project's scope.

The operational lifecycle is:

**Real-world observations → ingestion/QC → synchronized India digital state → analysis/modeling → forecast/risk → what-if experimentation → decision support → next state update**

This is the central architectural criterion used when deciding whether a feature is a Digital Twin capability or merely a supporting visualization/model.

## 2. Digital Twin versus adjacent technologies

| Technology | What it does | Role here |
|---|---|---|
| GIS | Represents geographic entities/layers | Visualization and spatial interaction |
| Dashboard | Presents information | User interface |
| Data lake/store | Stores data | Infrastructure |
| Simulation | Computes hypothetical system behavior | Scenario component |
| Forecast model | Predicts future values | Twin modeling component |
| ML predictor | Learns statistical relationships | Modeling component |
| Digital shadow | Digital state updated primarily one-way from the physical system | Partial precursor |
| Digital Twin | Maintains a connected, synchronized digital representation and uses it for prediction/simulation/decision support | Overall system architecture |

The project must therefore preserve the connection between source observations, the represented state, model outputs and subsequent state updates.

## 3. International systems studied

### NIST

NIST's Digital Twin work is useful for the core concepts: real-world counterpart, dynamic representation, synchronization, state/transition visibility, modeling and simulation, forecasting, decision support, interoperability and trust.

### Destination Earth / ECMWF

Destination Earth is substantially larger than this project, but its architecture provides reusable patterns: observations plus models, high-resolution simulation, extreme-event workflows and interactive **What Now / What Next / What If** reasoning. ECMWF describes its Extremes Digital Twin as combining Earth-system models, impact-sector models and observations and supporting tailored simulations and what-if scenarios.

The reusable lesson is architectural, not a claim that this repository matches DestinE's global scope or supercomputing capability.

## 4. India-specific climate representation

India's climate twin should be multi-variable over time and space. Relevant state dimensions include precipitation, temperature, humidity, wind, pressure, soil moisture, evapotranspiration, vegetation/land surface, ocean/coastal conditions and event indicators, subject to actual data availability.

The first connected national variable is IMD gridded rainfall. This provides a concrete, validated spatial state from which rainfall anomalies, extremes and hazard indicators can be derived.

Indian Earth-observation integration is represented through the ISRO/MOSDAC provider boundary. MOSDAC is an ISRO Space Applications Centre data centre that receives, processes and disseminates meteorological and oceanographic satellite data. Product-specific integration remains gated by data access, metadata and validation rather than being fabricated.

## 5. Current repository architecture audit

The repository currently contains:

- Next.js/React + MapLibre frontend;
- FastAPI backend;
- Xarray/NumPy/pandas scientific processing;
- IMD RF25 rainfall dataset and rainfall services;
- rainfall hazard/risk and extreme-event services;
- India administrative hierarchy;
- twin engine with synchronized observation-derived state;
- baseline forecast service and walk-forward validation;
- scenario engine;
- provenance/model/validation APIs;
- Sentinel-2/Prithvi-EO research pipeline for Chennai;
- MERRA-2/Prithvi-WxC contract/status layer;
- Vercel/Render deployment configuration and CI.

### What is already Digital Twin functionality

- reproducible observation-derived twin state;
- synchronization metadata and state hash;
- source/model provenance;
- national/state location context;
- state → forecast/risk/scenario relationship;
- repeatable state regeneration from observations.

### What remains ordinary supporting functionality

- MapLibre map rendering is GIS/visualization;
- charts are visualization;
- IMD rainfall is an observation source;
- the moving-average forecast is a model;
- risk scoring is an impact/risk model;
- Sentinel-2/Prithvi-EO inference is an EO modeling component.

They become part of the Digital Twin only when they operate on, update or inform the synchronized twin state.

## 6. Main gaps identified

1. Continuous multi-source ingestion is not yet operational.
2. The national state is strongest for rainfall; many atmospheric/environmental variables remain planned or dataset-gated.
3. Formal data assimilation is not yet implemented.
4. Probabilistic uncertainty/calibration is incomplete.
5. Temperature, hydrology/flood, drought, coastal and cyclone models require validated datasets and methods before activation.
6. Prithvi-WxC inference requires the official multi-variable MERRA-2 contract and substantial compute/storage.
7. The Chennai EO research subset is not equivalent to an India-wide EO state.
8. Persistent time-series/object storage and scheduled ingestion need to mature for production scale.
9. State/district aggregation must always use validated geometry/data and must never infer missing administrative metrics from national aggregates.

## 7. Target India Climate Digital Twin

```text
REAL-WORLD INDIA
      │
      ├── IMD / station observations
      ├── ISRO / MOSDAC / satellite observations
      ├── ERA5 / reanalysis
      ├── authoritative forecast products
      └── environmental datasets
      │
      ▼
INGESTION + QC + NORMALIZATION + PROVENANCE
      │
      ▼
INDIA DIGITAL TWIN STATE
      │
      ├── spatial location/grid
      ├── timestamp
      ├── variable/value
      ├── source/model
      ├── quality/freshness
      └── uncertainty/confidence when available
      │
      ├────────────┬─────────────┬───────────────┐
      ▼            ▼             ▼               ▼
STATE ESTIMATION FORECASTING   EXTREMES       SCENARIOS
      │            │             │               │
      └────────────┴─────────────┴───────────────┘
                           │
                           ▼
                    RISK / DECISION SUPPORT
                           │
                           ▼
                     MAP + API + UI
```

## 8. Model strategy

The project should not choose the most complicated model by default. The recommended progression is:

1. Strong statistical baseline.
2. Tree/time-series ML when sufficient features/history exist.
3. Spatial-temporal deep learning when enough gridded training data exists.
4. Prithvi-WxC for multi-variable weather/climate forecasting after its official input contract is satisfied.
5. Prithvi-EO for satellite/EO representation and downstream tasks.
6. Authoritative external event forecasts where independently recreating an operational meteorological model is not scientifically justified.

Model comparison should use temporal holdout or rolling evaluation. Continuous outputs should use MAE/RMSE/bias and, where useful, probabilistic scores. Event models should use precision/recall/F1, PR-AUC/ROC-AUC and calibration where the labelled sample supports them.

## 9. State contract

The conceptual twin-state record is:

```text
location_id
latitude / longitude
administrative level and ID
timestamp
variable
observed value
estimated value
forecast value
unit
anomaly
uncertainty
confidence
source
model
quality flag
last updated
provenance ID
```

A field is omitted or explicitly marked unavailable when its source does not support it. The API must never invent uncertainty or confidence.

## 10. Scenario semantics

The UI and API must distinguish three categories:

- **Observed:** derived from source observations.
- **Forecast:** generated by a predictive model from a forecast origin.
- **Scenario:** hypothetical input perturbation or simulation.

The current What-If engine is a rainfall-hazard sensitivity experiment. Temperature and sea-level inputs are recorded but not coupled to physical impacts until validated datasets/models exist.

## 11. Verification standard

Before enabling a new capability in the operational UI:

- validate its source and units;
- validate spatial and temporal coverage;
- check missing/stale data;
- perform temporal evaluation without future leakage;
- expose model identity and forecast origin;
- expose uncertainty/calibration status when available;
- test API failure/invalid-input paths;
- distinguish authoritative external products from project-generated predictions.

## 12. References

- NIST Digital Twins: https://www.nist.gov/digital-twins
- NIST Definitions and State of the Art: https://www.nist.gov/digital-twins/definitions-and-state-art
- NIST Essential Elements: https://www.nist.gov/digital-twins/essential-elements
- NIST Digital Twin Core Conceptual Models and Services: https://www.nist.gov/publications/digital-twin-core-conceptual-models-and-services
- NIST IR 8356: https://csrc.nist.gov/pubs/ir/8356/final
- ECMWF Extremes Digital Twin: https://www.ecmwf.int/en/forecasts/datasets/weather-induced-extremes-digital-twin-extremes-dt
- ECMWF Climate Change Adaptation Digital Twin: https://www.ecmwf.int/en/forecasts/dataset/destination-earth-digital-twin-climate-change-adaptation
- Destination Earth Digital Twins: https://destine.ecmwf.int/digital-twins/
- MOSDAC / ISRO: https://mosdac.gov.in/

## 13. Implementation status

This repository is an **India Climate Digital Twin core**, not a claim of being a full national operational Earth-system twin. The architecture is intentionally extensible: new validated variables/providers/models can update the same twin-state contract without replacing the existing rainfall/risk/forecast foundation.
