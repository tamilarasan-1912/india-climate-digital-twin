"""Local smoke test for the operational Digital Twin API.

Start FastAPI first, then run:
    python scripts/smoke_test_api.py
"""

from __future__ import annotations

import json
import sys
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

BASE = "http://127.0.0.1:8000"
ENDPOINTS = [
    "/",
    "/api/health",
    "/api/climate/variables",
    "/api/twin/summary",
    "/api/twin/state",
    "/api/forecast/baseline?horizon=7",
    "/api/models",
    "/api/validation",
    "/api/provenance",
    "/api/explain/rainfall?rainfall_mm=100",
    "/api/scenarios/simulate?base_date=2024-07-15&precipitation_delta_pct=20",
    "/api/risk/summary/2024-07-15",
    "/api/extreme-events/summary/2024-07-15",
]


def main() -> int:
    failures = []
    for endpoint in ENDPOINTS:
        try:
            with urlopen(BASE + endpoint, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
                print(f"PASS {response.status:3} {endpoint} ({type(payload).__name__})")
        except HTTPError as error:
            failures.append((endpoint, f"HTTP {error.code}"))
            print(f"FAIL {error.code:3} {endpoint}")
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            failures.append((endpoint, str(error)))
            print(f"FAIL     {endpoint} ({error})")

    print("-" * 72)
    print(f"Checked: {len(ENDPOINTS)}  Failed: {len(failures)}")
    if failures:
        for endpoint, reason in failures:
            print(f"  {endpoint}: {reason}")
        return 1
    print("ALL API SMOKE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
