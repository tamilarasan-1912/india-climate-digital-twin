"""Optional API-key/RBAC boundary for administrative APIs.

Public read endpoints remain public. Write/administrative routes can require
an operator key through ADMIN_API_KEY without storing credentials in source.
"""
from __future__ import annotations

from typing import Any
import hmac, os
from fastapi import HTTPException, Request

def require_operator(request: Request) -> None:
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        # Development mode: the operator boundary is disabled. This is reported
        # truthfully by operator_auth_status() rather than being presented as
        # an enforced authentication layer.
        return
    supplied = request.headers.get("x-api-key", "")
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="operator authentication required")


def operator_auth_status() -> dict[str, Any]:
    """Truthful state of the administrative boundary."""
    configured = bool(os.getenv("ADMIN_API_KEY", "").strip())
    return {
        "admin_api_key_configured": configured,
        "operator_boundary": "enforced" if configured else "disabled_development_mode",
        "public_read_apis": "open",
        "header": "x-api-key",
    }
