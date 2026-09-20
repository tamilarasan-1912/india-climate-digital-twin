"""Process-local rate limiter for API protection.

This limiter is per-process. Under horizontal scaling it must be replaced by a
shared store (for example Redis) to enforce a global limit; it is intentionally
not presented as a distributed solution.
"""
from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict, deque

from fastapi import HTTPException, Request

_BUCKETS: "OrderedDict[str, deque[float]]" = OrderedDict()
_LOCK = threading.Lock()
_MAX_TRACKED_CLIENTS = 10_000


def client_key(request: Request) -> str:
    """Derive a rate-limit key, trusting forwarded headers only if configured.

    ``x-forwarded-for`` is client-controlled unless a trusted proxy sets it, so
    it is honoured only when TRUST_PROXY_HEADERS is enabled.
    """
    if os.getenv("TRUST_PROXY_HEADERS", "false").strip().lower() in {"1", "true", "yes"}:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request) -> None:
    limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "240"))
    if limit <= 0:
        return
    now = time.time()
    key = client_key(request)
    with _LOCK:
        bucket = _BUCKETS.get(key)
        if bucket is None:
            bucket = deque()
            _BUCKETS[key] = bucket
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        bucket.append(now)
        _BUCKETS.move_to_end(key)
        # Evict idle clients so the limiter cannot grow without bound.
        while len(_BUCKETS) > _MAX_TRACKED_CLIENTS:
            _BUCKETS.popitem(last=False)


def reset_rate_limiter() -> None:
    with _LOCK:
        _BUCKETS.clear()
