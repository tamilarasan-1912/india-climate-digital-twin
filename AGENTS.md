# INDIA CLIMATE DIGITAL TWIN — Engineering Constitution

This repository implements an India-only climate Digital Twin.

## Non-negotiable rules

- India is the system boundary. Never convert the project into a global Earth System Digital Twin.
- Never fabricate climate observations, forecasts, satellite observations, model outputs, uncertainty, validation metrics, administrative boundaries, or district/city data.
- Missing data must be represented explicitly with `NO_DATA`, `NOT_CONNECTED`, `MODEL_NOT_READY`, `WAITING_FOR_CREDENTIALS`, or `COMPUTE_NOT_AVAILABLE` as appropriate.
- A map/dashboard is not the Digital Twin. The twin must maintain observations → validation/QC → digital climate state → synchronization → prediction → risk → What-If → validation against reality → state update.
- Every production climate value requires provenance.
- Never mark a source or model operational unless its actual ingestion/inference pipeline works.
- Never mark Prithvi-WxC operational unless its complete official input contract, normalization/statistics, compatible checkpoint, and suitable compute are available.
- Never use synthetic values in production.
- Never hardcode production climate metrics in the UI.
- Every UI control must perform a real function. No dead buttons, tabs, filters, map controls, or fake live indicators.
- Every new backend service requires tests.
- Every new data source requires validation and provenance.
- Every model requires validation against observations where applicable.
- District/city information must come from validated administrative data.
- Scientific correctness takes priority over visual appearance.
- Do not silently repair scientifically significant data.
- Do not declare completion merely because the repository builds.

## Completion gate

Completion requires a tested end-to-end path:

real observations → ingestion → QC → provenance → digital state → synchronization → forecast → risk → What-If → validation → resynchronization.

Maintain accurate documentation of COMPLETE, PARTIAL, BLOCKED, and NOT IMPLEMENTED capabilities.
