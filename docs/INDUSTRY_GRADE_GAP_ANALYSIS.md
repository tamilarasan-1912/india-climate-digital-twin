# India Climate Digital Twin — Industry-Grade Gap Analysis

This document maps the requested Bharat Climate Twin product blueprint against the current repository and defines the implementation order. It intentionally separates **implemented**, **partially implemented**, and **not yet implemented** capabilities.

## Current assessment

| Capability | Status | Evidence / next build |
|---|---|---|
| Digital-twin state + provenance | BUILT | Twin state contract, state envelope, state hash |
| What Now | BUILT | `/api/twin/now` and observation-derived state |
| What Next baseline | BUILT | validated moving-average benchmark |
| Prithvi-WxC integration | PARTIAL | official runtime + forecast endpoint; requires real MERRA-2, climatology and runtime assets |
| State-level climate aggregation | BUILT | polygon/grid aggregation over IMD rainfall |
| National GIS | PARTIAL | existing geospatial UI/data; needs full operational layer catalog |
| Multi-variable atmospheric forecast | PARTIAL | contract and official rollout adapter; needs operational MERRA-2 asset pipeline and validation |
| Multi-hazard engine | PARTIAL | rainfall hazard is operational; heat/wind are screening indicators only |
| Flood physics | NOT BUILT | requires DEM, drainage, rainfall-runoff and hydraulic model |
| Urban heat twin | NOT BUILT | requires LST/land-cover/building/urban morphology pipeline |
| Agriculture twin | NOT BUILT | requires crop, soil, weather and phenology/yield models |
| Coastal/cyclone twin | NOT BUILT | requires cyclone, surge, DEM/bathymetry and coastal model |
| Industrial/asset twin | NOT BUILT | requires asset registry, exposure and vulnerability functions |
| Financial loss model | NOT BUILT | requires consequence/cost and vulnerability functions |
| Scenario engine | PARTIAL | rainfall sensitivity is operational; physical multi-hazard coupling is pending |
| Early warning workflow | NOT BUILT | alert rules, channels, escalation and acknowledgement needed |
| Multilingual alerts | NOT BUILT | notification service + Indian-language templates needed |
| Asset registry | NOT BUILT | common asset schema + spatial persistence needed |
| Exposure/vulnerability | NOT BUILT | population, infrastructure and sector datasets needed |
| Long-term 2030/2050/2100 scenarios | NOT BUILT | downscaled climate projections + scenario metadata needed |
| Enterprise reporting | NOT BUILT | BRSR/ISSB/TCFD/CDP report generators needed |
| Data catalog / STAC | NOT BUILT | dataset registry, licenses, lineage and update metadata needed |
| Lakehouse/object storage | NOT BUILT | S3/Zarr/Iceberg-style production data plane needed |
| Streaming/Kafka | NOT BUILT | event ingestion infrastructure needed |
| IAM/SSO/RBAC | NOT BUILT | production identity layer needed |
| Audit/security controls | PARTIAL | repository CI/provenance exists; production security controls are pending |
| Observability | PARTIAL | application health exists; Prometheus/OpenTelemetry/Grafana stack pending |
| Kubernetes/IaC | NOT BUILT | deployment manifests and Terraform/Helm needed |

## Implementation strategy

Do not attempt the entire national product at once. Build the common platform primitives first, then one production-grade pilot domain.

### Track A — platform foundation

1. Common state/data/risk contracts.
2. Asset and location model.
3. Provenance, uncertainty and data-quality metadata.
4. Versioned API namespace.
5. Dataset catalog and ingestion interfaces.
6. Authentication/authorization boundary.
7. Audit and observability contracts.

### Track B — climate intelligence

1. IMD rainfall observation state.
2. MERRA-2 atmospheric state.
3. Prithvi-WxC forecast.
4. Temperature/heat screening.
5. Wind/extreme-weather screening.
6. Forecast validation and model registry.

### Track C — Chennai/Mumbai-style pilot

1. DEM + land use + drainage.
2. Rainfall-runoff model.
3. 2D flood model.
4. Asset exposure.
5. Ward/asset risk scoring.
6. Alert workflow.
7. Incident report generation.

### Track D — enterprise resilience

1. Facility onboarding.
2. Asset inventory.
3. Hazard × exposure × vulnerability.
4. Expected annual loss.
5. Adaptation cost/residual risk.
6. Disclosure/report export.

## Non-negotiable scientific rules

- A dashboard is not a digital twin by itself.
- A forecast model is not the twin by itself.
- Missing variables remain unavailable; they are never fabricated.
- A screening indicator must not be labelled as calibrated probability.
- Scenario inputs are only physically coupled when the corresponding validated model exists.
- Every operational result must carry timestamp, source, model version, spatial/temporal resolution and validation status.
- Large model weights and climate archives must remain external dependencies; normal web requests must not download multi-GB assets.

## MVP target

The first industry-grade milestone is a **single Indian metropolitan climate-risk twin** with:

- current rainfall/temperature state;
- 24–72 hour forecast;
- urban flood model;
- heat-risk model;
- asset registry;
- asset-level risk;
- multilingual alert generation;
- auditable provenance;
- scenario comparison;
- API-first delivery.

The national platform then becomes a scale-out of the same contracts rather than a rewrite.
