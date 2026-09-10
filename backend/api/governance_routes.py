"""Operational governance endpoints for authorised government users."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Query, Request

from backend.services.governance_service import authenticate, audit_event, can, recent_audit_events, security_status
from backend.services.operations_service import get_operations_status

router = APIRouter(prefix="/api/governance", tags=["Government Governance"])


def _identity(api_key: str | None) -> dict:
    identity = authenticate(api_key)
    if not identity["authenticated"] and identity["auth_mode"] != "disabled":
        raise HTTPException(status_code=401, detail="Government authentication required")
    return identity


def _require(identity: dict, permission: str) -> None:
    if identity["auth_mode"] == "disabled":
        return
    if not can(identity.get("role"), permission):
        raise HTTPException(status_code=403, detail=f"Role does not have '{permission}' permission")


@router.get("/security")
def governance_security(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    identity = _identity(x_api_key)
    _require(identity, "manage")
    return security_status()


@router.get("/identity")
def governance_identity(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    identity = _identity(x_api_key)
    return {"authenticated": identity["authenticated"], "role": identity["role"], "auth_mode": identity["auth_mode"]}


@router.get("/audit")
def governance_audit(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    identity = _identity(x_api_key)
    _require(identity, "manage")
    events = recent_audit_events(limit)
    audit_event(
        action="audit.read",
        resource="audit_events",
        actor_role=identity.get("role"),
        request_id=request.headers.get("X-Request-ID"),
        source_ip=request.client.host if request.client else None,
        details={"limit": limit},
    )
    return {"events": events, "count": len(events)}


@router.get("/operations")
def governance_operations(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    identity = _identity(x_api_key)
    _require(identity, "read")
    result = get_operations_status()
    audit_event(
        action="operations.read",
        resource="national_operations_status",
        actor_role=identity.get("role"),
        request_id=request.headers.get("X-Request-ID"),
        source_ip=request.client.host if request.client else None,
        details={"overall_status": result["overall_status"]},
    )
    return result
