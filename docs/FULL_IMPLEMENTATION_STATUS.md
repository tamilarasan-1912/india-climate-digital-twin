# Full India Climate Digital Twin implementation status

## Implemented in this phase

- Multi-variable climate-state assembler with explicit `available` / `no_data` states.
- Transparent weighted observation/reanalysis assimilation primitive with source weights and spread-based uncertainty.
- Multi-hazard screening for rainfall extremes, rainfall flood screening, heat, wind and heat-stress screening when required datasets exist.
- District and city GeoJSON adapters that return `no_data` until validated administrative geometry is installed.
- FastAPI endpoints for the multi-variable state, variable discovery, multi-hazard state and district/city resources.
- Automated tests for assimilation and the no-fabrication policy.

## Existing operational core

- IMD RF25 rainfall observations.
- India-wide state aggregation against state polygons.
- Rainfall anomalies and risk grids.
- Extreme rainfall detection and GeoJSON.
- Historical rainfall API.
- Baseline what-next forecast.
- Rainfall what-if sensitivity simulation.
- Provenance, validation, model registry and health endpoints.
- Prithvi-EO historical feature pipeline.
- Prithvi-WxC readiness contract.

## Remaining scientific integrations

These cannot be honestly completed by code alone without the corresponding validated datasets/model assets:

1. Continuous IMD operational ingestion.
2. MOSDAC INSAT-3D/3DR/3DS operational ingestion and product authentication/availability.
3. National temperature, wind and humidity datasets in `backend/data/climate/`.
4. District and city boundary datasets in the documented GeoJSON locations.
5. Full MERRA-2 160-variable two-timestamp tensor construction and preprocessing for Prithvi-WxC.
6. Prithvi-WxC 2.3B checkpoint and a GPU-capable inference runtime.
7. Hydrologic rainfall-runoff/inundation model for actual flood prediction.
8. Validated drought, coastal inundation and sectoral impact models.
9. Calibrated uncertainty and probabilistic forecast validation.
10. Production scheduler/object storage/monitoring for continuous synchronization.

The application deliberately reports these as unavailable rather than fabricating results.

## Data locations

Place validated NetCDF climate datasets under:

`backend/data/climate/`

The multi-variable state assembler discovers supported variables by NetCDF variable aliases and exposes provenance for the selected file.

District geometry:

`public/data/india/india-districts.geojson`

City geometry:

`public/data/india/india-cities.geojson`

## Scientific boundary

This remains an India Climate Digital Twin, not a global Earth-system digital twin. Multi-hazard outputs are screening results until domain-specific physical impact models and validation are connected.
