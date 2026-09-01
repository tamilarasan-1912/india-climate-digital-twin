# MERRA-2 input directory

Place validated MERRA-2 NetCDF files here. Do **not** commit large raw files to
normal Git history.

The Prithvi WxC rollout model expects two timestamps and 160 atmospheric
variables on the MERRA-2-compatible grid. The validator in
`backend/services/merra2_input_validator.py` performs structural checks before
any model inference is attempted.

Recommended workflow:

1. Obtain the required MERRA-2 fields from the official NASA/GES DISC source.
2. Store the files locally in this directory.
3. Run `python backend/services/merra2_input_validator.py`.
4. Check `/api/ai/prithvi/status`.
5. Only after the input contract passes, run the optional AI environment.
