# Repository working notes

## Environment
- Run tests from the repository root: `python -m unittest discover -s backend/tests -p "test_*.py"`.
- `fastapi.testclient` is unusable here (starlette wants `httpx2`). For API smoke tests start uvicorn on a spare port and use `curl` instead.
- Frontend checks: `npx tsc --noEmit`, `npm run lint`, `npm run build`.

## Data and honesty rules
- Never fabricate climate values. Unavailable data returns `status: "NO_DATA"` / `no_data`, never zeros or placeholders.
- District rainfall is real IMD 0.25-degree grid aggregation over geoBoundaries ADM2 polygons (`backend/services/district_climate_service.py`). Districts whose polygon contains no grid-cell centre report no coverage; they are excluded, not filled.
- District geometry lives in `backend/data/admin_cache/IND-ADM*.geojson` and is served via `administrative_boundary_service`. Do not add a second copy of the same dataset under a new filename.
- Admin name matching goes through `backend/services/admin_names.py::normalise_admin_name` so diacritics ("Tamil Nādu") and plain ASCII queries agree. Keep using it for any new admin matching.
- `climate_intelligence_service` answers only from connected services. Add new intents there rather than in the API layer.

## API
- All route handlers wrap service calls in `_call`, which maps `ValueError` to 400, `FileNotFoundError`/`RuntimeError` to 503, and everything else to 500. Raise `ValueError` for bad user input.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
