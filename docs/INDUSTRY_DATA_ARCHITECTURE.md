# Industry Data Architecture

## Design principle

The database is the system of record for metadata, vector features, assets,
risk results, scenarios and audit events. Large climate rasters, model tensors
and satellite archives remain in object storage and are discovered through
STAC. This prevents the operational API from becoming a file server.

## Standards

- STAC 1.1 for spatiotemporal asset discovery.
- OGC API - Features for interoperable feature access.
- Cloud Optimized GeoTIFF for web-native raster distribution.
- PostGIS for authoritative vector/spatial transactional data.
- NetCDF/Zarr for multidimensional scientific arrays.
- JSON/GeoJSON for API-facing feature exchange.

## Data lifecycle

```text
Source/API/Sensor
      |
      v
Ingestion adapter -> validation/QC -> provenance/hash
      |
      +----> Object storage (COG/Zarr/NetCDF)
      |
      +----> STAC catalog
      |
      v
PostGIS metadata + spatial features
      |
      v
Twin state / feature generation
      |
      +--> Forecast models
      +--> Hazard models
      +--> Exposure/vulnerability
      |
      v
Risk + scenario + alert results
      |
      v
API / GIS / reports
```

## Provenance requirements

Every operational result must be traceable to:

- dataset identifier and provider;
- acquisition/valid timestamps;
- source asset URI;
- content hash where practical;
- preprocessing/regridding version;
- model name/version/checksum;
- validation status;
- spatial and temporal resolution;
- limitations and uncertainty metadata.

## Production scaling

The initial PostgreSQL/PostGIS deployment can support the pilot. For national
scale, partition time-series tables, move multidimensional arrays to object
storage/Zarr, introduce an event bus for ingestion, and expose OGC-compatible
APIs through a geospatial service tier. Do not make the frontend dependent on
a particular cloud provider.
