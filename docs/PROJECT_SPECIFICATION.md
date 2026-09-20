# India Climate Digital Twin — Master Project Specification

## Scope

India is the system boundary. The product is a real climate Digital Twin, not a dashboard and not a global Earth System Digital Twin.

## Core lifecycle

Real India observations → ingestion → quality control → provenance → data assimilation/fusion → India digital climate state → synchronization → AI/statistical forecasting → What-Next → risk/extreme-event intelligence → What-If scenarios → validation against observations → updated twin state.

## Authoritative data layers

Use authoritative sources where technically and legally available:

- IMD rainfall and weather APIs
- ISRO MOSDAC rainfall and INSAT products
- ERA5
- NASA MERRA-2
- Prithvi-WxC
- Prithvi-EO
- INCOIS
- Central Water Commission
- IITM/CORDEX South Asia
- ECMWF IFS/AIFS benchmarking where available
- Sentinel-2 and other validated EO products
- authoritative administrative boundaries

Never represent synthetic or placeholder values as production observations, forecasts, uncertainty, validation results, or administrative facts.

## Digital state contract

Supported hierarchy: India → State/UT → District → City, only where validated administrative data and climate data exist.

Each production state value should carry location, timestamp, variable, value, unit, source, model, quality flag, scientifically justified uncertainty/confidence, last updated time, and provenance ID.

The platform maintains source registry, data catalog, ingestion manifests, QC reports, freshness, provenance, state hashing/versioning, and synchronization metadata.

## Model rules

Maintain an operational baseline forecast. Prithvi-WxC remains gated until the real official input contract is satisfied: 160 variables, 2 timesteps, 6-hour interval, required static fields, correct dimensions, official normalization/statistics, compatible checkpoint, and suitable compute.

Forecasts must be validated against actual observations with appropriate deterministic and event/probabilistic metrics.

Prithvi-EO is used only through a real EO pipeline with validated inputs and provenance.

## Risk and scenarios

Support scientifically honest heavy/extreme rainfall, flood screening, drought, heat, heat stress, wind, cyclone context, and coastal risk only where supported by validated data/models. Separate hazard, exposure, vulnerability and risk.

What-If scenarios must expose baseline, scenario, perturbation, model, coupled and uncoupled variables, outputs, uncertainty, and limitations. A sensitivity experiment must not be mislabeled as a physical simulation.

## UI modules

National Command Center; Digital Twin State; Live Observations; Climate Explorer; Forecast/What-Next; Scenario Lab/What-If; Risk Monitor; Extreme Event Monitor; Historical Climate; State Explorer; District Explorer; City Explorer; Satellite Intelligence; Flood Intelligence; Heat Intelligence; Monsoon Intelligence; Data Catalog; Data Quality; Model Registry; Model Validation; Provenance; System Operations; Security/Governance; Reports; Settings.

Every control must have real behavior. No dead UI and no hardcoded production climate metrics.

## API and platform

FastAPI backend with typed contracts, validation, structured errors, request IDs, restricted CORS, security headers, authentication/RBAC, and audit logging.

Provide endpoints for health/status, data, hierarchy, climate state, regional twins, rainfall, historical climate, forecasts, Prithvi-WxC status/inference, risk, extremes, scenarios, validation, satellite, operations, governance, and reports.

## Scientific integrity

Validate NaN/infinity, missing values, duplicates, coordinates, timestamps, units, physical ranges, temporal/spatial gaps, schema changes, source versions, and freshness. Do not silently repair scientifically significant data.

## Testing and completion

Maintain unit, integration, API, data-contract, spatial, forecast-validation, synchronization, scenario, frontend, E2E, and security tests. Exercise missing data and external failures. CI must remain green.

Do not place large climate datasets or ~28 GB model checkpoints in ordinary frontend deployment artifacts.

Completion requires the end-to-end real-data → state → synchronization → forecast → risk → What-If → validation → resynchronization path, plus full test/build/deployment verification and an accurate `docs/FINAL_IMPLEMENTATION_STATUS.md` classifying each major capability as COMPLETE, PARTIAL, BLOCKED, or NOT IMPLEMENTED.
