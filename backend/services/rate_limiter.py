"""Process-local rate limiter for administrative/API protection."""
from __future__ import annotations
import os, time
from collections import defaultdict, deque
from fastapi import HTTPException, Request

_BUCKETS: dict[str, deque[float]] = defaultdict(deque)

def enforce_rate_limit(request: Request) -> None:
    limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    now = time.time()
    key = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
    bucket = _BUCKETS[key]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    bucket.append(now)
