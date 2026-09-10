"""Small standard-library helpers for production API operations hardening.

The service is intentionally stateless. It creates request identifiers and
builds conservative response/security headers without exposing secrets.
"""
from __future__ import annotations

from uuid import uuid4
from typing import Mapping


REQUEST_ID_HEADER = "X-Request-ID"


def request_id(existing: str | None = None) -> str:
    """Return a bounded request/correlation id suitable for logs and audit."""
    candidate = (existing or "").strip()
    if 0 < len(candidate) <= 128 and all(ch.isalnum() or ch in "-_.:" for ch in candidate):
        return candidate
    return uuid4().hex


def security_headers() -> Mapping[str, str]:
    """Return security headers safe for JSON API responses."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }
