# MERRA-2 input staging

Place authenticated MERRA-2 NetCDF downloads in this directory. Raw files are intentionally not committed to normal Git history.

The Prithvi WxC rollout model expects two timestamps and 160 atmospheric variables on the MERRA-2-compatible grid. The validator performs structural checks before inference.

## Preparation

Run:

```bash
python scripts/prepare_merra2_prithvi_input.py
```

or:

```bash
python scripts/prepare_merra2_prithvi_input.py --input backend/data/merra2/<file>.nc
```

The preparation step discovers a real local MERRA-2 NetCDF, verifies time/latitude/longitude coordinates, requires at least two timestamps and 160 atmospheric fields, crops to the Chennai bounding box when possible, checks selected fields for NaNs, and writes a traceable prepared NetCDF plus JSON manifest.

It never creates synthetic missing atmospheric variables. A file with fewer than 160 variables is correctly reported as **not ready** rather than padded with fabricated data.

The final Prithvi-WxC adapter must still enforce the model's exact variable ordering, units, normalization and tensor layout before inference.
