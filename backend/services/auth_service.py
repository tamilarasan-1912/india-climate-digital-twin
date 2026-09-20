"""Optional API-key/RBAC boundary for administrative APIs.

Public read endpoints remain public. Write/administrative routes can require
an operator key through ADMIN_API_KEY without storing credentials in source.
"""
from __future__ import annotations
import hmac, os
from fastapi import HTTPException, Request

def require_operator(request: Request) -> None:
    expected = os.getenv("ADMIN_API_KEY", "").strip()
    if not expected:
        return
    supplied = request.headers.get("x-api-key", "")
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="operator authentication required")
