# Prithvi-WxC Runtime Plan

## Scope

Prithvi-WxC is an India Climate Digital Twin forecasting component. It is not the digital twin itself and does not expand the project into a global Earth-system twin.

## Readiness gates

1. Valid MERRA-2 assets are present.
2. At least two timestamps are available at the required six-hour interval.
3. The validated input contract contains the required 160 variables.
4. Official variable ordering and normalization/statistics are available.
5. Required static fields and spatial dimensions are validated against the rollout configuration.
6. Model checkpoint is available in an external runtime; it is not committed to GitHub, Vercel, Render, or the Codespace repository.
7. Runtime has sufficient memory/GPU resources for the 2.3B-parameter model.
8. Inference output passes shape, finite-value, coordinate, and provenance checks.

## Data integrity rule

The implementation must never create missing atmospheric variables by guessing, copy-filling, or using the rainfall-only IMD dataset. If a prerequisite is absent, the API returns a blocked/readiness state.

## Deployment boundary

The lightweight FastAPI service remains responsible for validation and orchestration. Heavy model inference should run in a GPU-capable external runtime or batch worker, with forecast artifacts returned to the India Climate Twin API/storage layer.

## Current state

The repository has structural MERRA-2 contract inspection and readiness endpoints. Actual tensor construction remains gated until the official model manifest/statistics and compatible MERRA-2 assets are supplied.
