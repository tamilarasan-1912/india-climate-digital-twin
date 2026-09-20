# India Administrative Geography Source

## Authoritative source
The primary administrative boundary source for the India Climate Digital Twin is the **Survey of India Administrative Boundary Database (ABDB)**.

The Online Maps Portal publishes an India-wide administrative boundary product up to district level and a separate product up to taluk/sub-district level. The district-level product is the target source for the national state → district Digital Twin hierarchy.

Official portal: https://onlinemaps.surveyofindia.gov.in/

## Integration policy

- Treat Survey of India geometry as authoritative administrative reference data.
- Preserve the source product/code and acquisition date in metadata.
- Convert source geometry to GeoJSON only as a derived application format; do not change feature identity or geometry semantics.
- Maintain stable internal IDs separately from display names.
- Never infer a district or city metric from a national aggregate.
- A missing or unvalidated boundary dataset must remain `no_data`.
- City-level Digital Twin metrics require an independently validated city/urban boundary dataset; district boundaries are not a substitute.

## Target repository locations

```text
data/india/admin/survey_of_india/
  raw/                  # source downloads; not committed unless policy permits
  processed/            # validated derived GeoJSON/Parquet
  manifest.json         # source metadata, checksum, acquisition date
```

The repository should not invent a public download URL for a Survey of India product. The download should be obtained through the official portal's published product/Quick Access flow, then recorded in the manifest with its checksum.
