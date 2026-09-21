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

## Runtime geometry resolution

The running application resolves the `India -> State -> District` spine from
**geoBoundaries** (ADM1/ADM2, ODbL 1.0), which is the open source currently
installed in the repository. Survey of India ABDB remains the intended
authoritative replacement; the resolver below is unchanged when that swap
happens.

`backend/services/administrative_boundary_service.py` fetches geometry lazily
and caches it in `backend/data/admin_cache/`. That directory is gitignored, so
a fresh clone starts with no geometry on disk.

Resolution order for each administrative level:

1. A cache file newer than `ADMIN_BOUNDARY_CACHE_TTL` (default 21600s) is used as-is.
2. Otherwise the provider is contacted; a well-formed `FeatureCollection` is written to the cache.
3. If the provider is unreachable, times out, or returns malformed data, the last
   known-good cache file is served with a warning logged at WARNING level.
4. If there is no usable cache either, the request fails with `RuntimeError`.

Step 4 maps to **HTTP 503** ("Required scientific dataset, provider or model is
unavailable") through the API error mapper. It is never reported as HTTP 400,
because a missing provider is not a client input error.

`UNAVAILABLE` is the truthful state here: the platform does not synthesise
geometry. Cached geometry from a previous successful fetch is reused because it
is real observation data, not a substitute value.

### Reading a deployment status

| Symptom | Meaning |
| --- | --- |
| `/api/india/districts` returns 200 | Geometry served from cache or provider. |
| WARNING `serving cached geometry` in logs | Provider unreachable; last known-good geometry in use. |
| `/api/india/districts` returns 503 | No cache and no provider. Run once with egress to populate `backend/data/admin_cache/`. |
| `/api/india/districts` returns 400 | Genuine invalid input (for example an unknown state). |

### Configuration

- `ADMIN_BOUNDARY_CACHE_TTL` — seconds before a cached level is considered stale
  and refreshed from the provider. Raising it reduces provider dependence at the
  cost of slower upstream updates.
