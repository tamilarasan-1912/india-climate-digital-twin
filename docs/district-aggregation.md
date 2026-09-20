# District Climate Aggregation

## Purpose

The digital twin supports the geographic hierarchy:

```text
India → State / UT → District → IMD 0.25° grid cell
```

District metrics are produced by intersecting real IMD rainfall grid-point
centres with real administrative polygons. Nothing is interpolated, inferred, or
substituted from a parent region.

## Data sources

| Layer | Source | Licence | Notes |
|---|---|---|---|
| Rainfall | IMD RF25 (`RF25_ind2024_rfp25.nc`) | IMD open data | 0.25° grid, 129×135, 366 days |
| District geometry | geoBoundaries ADM2 (IND) | ODbL 1.0 | 735 districts, cached in `backend/data/admin_cache/` |
| State geometry | repository `india-states.geojson` | see repository | Used for state aggregation |

Geometry is never treated as a climate observation. It is only the geographic
spine used to drill down.

## Method

1. Load the IMD grid coordinates (129 latitudes × 135 longitudes).
2. Build an STRtree over the 735 district polygons.
3. For every grid-point centre, locate the covering district(s) with an exact
   `covers` predicate (candidates filtered by the R-tree).
4. Group cells by district using a stable sort, giving contiguous slices.
5. Compute statistics only over cells whose rainfall value is finite.

Aggregated statistics: `mean`, `median`, `minimum`, `maximum`, `valid_grid_cells`,
`mean_hazard_score`, `maximum_hazard_score`, `risk_category`.

The cell-to-district assignment depends only on the grid shape, so it is cached
and reused across dates. A full national aggregation runs in roughly two seconds.

## Honest handling of missing coverage

A district polygon may contain no IMD grid-point centre. This is common for very
small territories (Daman, Diu, Mahé, Kāraikāl, Yanam) and for island groups where
the IMD grid masks the open ocean. In that case the API returns:

```json
{
  "status": "no_grid_coverage",
  "valid_grid_cells": 0,
  "mean_rainfall_mm": null,
  "maximum_rainfall_mm": null,
  "risk_category": "no_data",
  "data_coverage": {
    "grid_cells_in_district": 0,
    "grid_coverage_percent": 0.0,
    "unavailable_reason": "district polygon contains no IMD 0.25-degree grid-point centre"
  }
}
```

A missing value is never coerced to `0`, and a district is never given the value
of its parent state or a neighbouring district.

## Name normalisation

geoBoundaries ADM2 carries diacritics and legacy spellings (`Tamil Nādu`,
`Mahārāshtra`, `Telangāna`) while the rest of the platform uses ASCII canonical
names. `district_climate_service.normalise_admin_name` folds both sides to
comparable ASCII before matching, and `canonical_state_name` restores the
hierarchy's spelling in API responses.

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/india/districts/coverage` | District geometry coverage |
| `GET /api/india/districts/climate/{date}` | All 735 districts for a date |
| `GET /api/india/state/{state_id}/districts/climate/{date}` | Districts under one state |
| `GET /api/india/district/{district_id}/climate/{date}` | One district |

Unknown district or state identifiers return HTTP 400, consistent with the rest
of the hierarchy endpoints. An out-of-range observation date returns HTTP 400.

## Validation

`backend/tests/test_district_climate_service.py` asserts:

- district identifiers are unique and geometry parses
- statistics satisfy `min ≤ mean ≤ max` and non-negativity
- districts without grid coverage return `null` metrics, not zero
- every district reports `data_coverage`
- a district maximum can never exceed the containing state's maximum
- single-district and bulk results agree
- unknown identifiers and invalid dates are rejected

## Current coverage

For 2024-07-15: 702 of 735 districts have data; 33 report `no_grid_coverage` for
the reasons above. Tamil Nadu resolves 37 of its 38 districts.
