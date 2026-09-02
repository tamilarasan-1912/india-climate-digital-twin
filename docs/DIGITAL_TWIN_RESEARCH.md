# Digital Twin Research and Implementation

## 1. What a digital twin is

The project follows the Earth-system interpretation of a digital twin rather than treating a dashboard or a prediction model as the twin itself.

A useful operational pattern is:

**Observed Earth system -> data ingestion -> synchronized digital state -> models -> forecast / impact assessment -> what-if scenarios -> decision support**

NIST describes a digital twin as a virtual representation of a real-world entity and emphasizes dynamic representation, connection and synchronization, forecasting, simulation, monitoring, diagnosis and decision support. NASA's Earth System Digital Twin work describes three major capabilities: a continuously updated digital replica, dynamic forecasting models, and impact assessment. Destination Earth uses the closely related **What Now / What Next / What If** pattern for Earth-system digital twins.

For this project, the physical counterpart is the climate/weather state over India. There is no physical actuator to control; the feedback loop is therefore observational and analytical: new observations update the digital state, models operate on that state, and scenario/impact results support human decisions.

## 2. Requirements derived from the research

| Digital-twin requirement | Project implementation |
|---|---|
| Real-world counterpart | India climate/weather system represented by gridded observations and reanalysis |
| Continuous or repeatable synchronization | `twin_engine.build_twin_snapshot()` derives the state directly from the current source dataset |
| Digital state | Observation-derived state vector plus rainfall/risk state |
| Provenance | Source dataset, variable, model and state hash are returned by the API |
| What Now | `/api/twin/now` |
| What Next | `/api/twin/next` |
| What If | `/api/twin/what-if` and `/api/scenarios/simulate` |
| Forecasting | Validated 7-day moving-average rainfall baseline; Prithvi-WxC remains gated by its input contract |
| Impact/risk assessment | Rainfall Hazard Index and spatial risk grid |
| Validation | Walk-forward baseline metrics and risk-engine checks |
| Interoperability | JSON APIs and GeoJSON spatial layers |
| Trust | Explicit data availability, model status and limitations; no fabricated missing variables |

## 3. Current twin state construction

The current operational state is intentionally deterministic and auditable. For a selected observation date it contains:

- India-wide rainfall minimum, median, mean and maximum.
- 7-day rolling rainfall mean.
- 30-day rainfall anomaly and anomaly z-score when sufficient history exists.
- Spatial rainfall hazard mean and maximum.
- Spatial risk distribution.
- Maximum-risk location from the rainfall hazard grid.
- A compact state vector containing those variables.
- A SHA-256-derived state hash so the same source state can be reproduced and identified.

This is a **data-driven state representation**, not a claim that the vector is a learned neural latent representation.

## 4. Forecasting layer

The forecast layer uses the existing walk-forward-validated 7-day moving-average baseline. It only uses observations up to the forecast origin and never uses future observations. This provides a reproducible benchmark while the Prithvi-WxC integration is being completed.

Prithvi-WxC is not substituted with fabricated data. Its official input contract requires compatible multi-variable atmospheric fields, so the model is only exposed when that contract is satisfied.

## 5. What-if layer

The scenario engine perturbs rainfall and recomputes the rainfall hazard field. Temperature and sea-level parameters are accepted and recorded but are not silently converted into fake physical impacts. They remain explicitly marked as uncoupled until validated temperature and coastal/flood models are added.

This makes the current scenario a **rainfall-hazard sensitivity experiment**, not a physical flood or climate-impact simulation.

## 6. Architecture

```text
                 OBSERVATIONS / REANALYSIS
                 IMD RF25 | ERA5 | Sentinel-2
                           |
                           v
                 +-----------------------+
                 | Data validation / QC   |
                 +-----------------------+
                           |
                           v
                 +-----------------------+
                 | DIGITAL TWIN STATE     |
                 | now + provenance       |
                 +-----------------------+
                    /          |          \
                   /           |           \
                  v            v            v
             Risk engine   Forecast      EO features
                  |            |            |
                  +------------+------------+
                               |
                               v
                     WHAT-NEXT / WHAT-IF
                               |
                               v
                     Dashboard / decisions
```

## 7. Research sources

- NIST Digital Twins: https://www.nist.gov/digital-twins
- NIST Essential Elements: https://www.nist.gov/digital-twins/essential-elements
- NIST Digital Twin Core Conceptual Models and Services: https://www.nist.gov/publications/digital-twin-core-conceptual-models-and-services
- NIST IR 8356: https://csrc.nist.gov/pubs/ir/8356/final
- ISO 23247-1:2021: https://www.iso.org/standard/75066.html
- NASA Earth Systems Digital Twins: https://esto.nasa.gov/earth-system-digital-twin/
- NASA ESDT technical report: https://ntrs.nasa.gov/citations/20240000303
- Destination Earth Digital Twins: https://destination-earth.eu/destination-earth/destines-components/digital-twins-digital-twin-engine/
- Destination Earth Digital Twin FAQ: https://destination-earth.eu/faq/what-are-destines-digital-twins/
- Destination Earth Climate Adaptation Digital Twin: https://destination-earth.eu/faq/what-is-the-climate-change-adaptation-digital-twin/

## 8. Important scope statement

A production national Earth-system digital twin requires substantially more than this repository currently contains: continuous multi-source ingestion, multi-variable atmospheric/ocean/land observations, data assimilation, calibrated numerical/AI forecasting, sectoral impact models, uncertainty quantification, high-performance computing and operational data infrastructure.

The implementation in this repository therefore provides a **working, auditable climate digital-twin core** around the datasets and models that are actually available. It does not claim that the project is already equivalent in resolution, coverage, compute or scientific fidelity to NASA ESDT or Destination Earth.
