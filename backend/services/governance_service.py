"""Government-grade governance primitives for the India Climate Digital Twin.

This module intentionally uses only the Python standard library. It provides:
- configurable API-key/RBAC authentication for protected deployments;
- structured audit events persisted to SQLite;
- security-oriented request metadata without storing secrets;
- role/permission definitions suitable for government operations.

Authentication is disabled by default so the scientific demo remains usable.
Production deployments should set GOVERNMENT_AUTH_ENABLED=true and provide
API keys through environment/secret management rather than source control.
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROLES: dict[str, set[str]] = {
    "administrator": {"read", "operate", "analyse", "simulate", "manage"},
    "national_operator": {"read", "operate", "analyse", "simulate"},
    "state_operator": {"read", "operate", "analyse", "simulate"},
    "analyst": {"read", "analyse", "simulate"},
    "viewer": {"read"},
}

DEFAULT_ROLE = "viewer"
AUDIT_DB = Path(os.getenv("AUDIT_DB_PATH", "backend/data/governance/audit.sqlite3"))


def auth_enabled() -> bool:
    return os.getenv("GOVERNMENT_AUTH_ENABLED", "false").lower() in {"1", "true", "yes", "on"}


def _api_keys() -> dict[str, str]:
    """Read role:key pairs from GOVERNMENT_API_KEYS without exposing keys."""
    raw = os.getenv("GOVERNMENT_API_KEYS", "")
    result: dict[str, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item or ":" not in item:
            continue
        role, key = item.split(":", 1)
        if role in ROLES and key:
            result[key] = role
    return result


def authenticate(api_key: str | None) -> dict[str, Any]:
    if not auth_enabled():
        return {"authenticated": False, "role": "system_demo", "auth_mode": "disabled"}
    if not api_key:
        return {"authenticated": False, "role": None, "auth_mode": "api_key"}
    role = _api_keys().get(api_key)
    return {"authenticated": role is not None, "role": role, "auth_mode": "api_key"}


def can(role: str | None, permission: str) -> bool:
    return bool(role and permission in ROLES.get(role, set()))


def _connection() -> sqlite3.Connection:
    AUDIT_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(AUDIT_DB)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_time TEXT NOT NULL,
            actor_role TEXT,
            action TEXT NOT NULL,
            resource TEXT,
            outcome TEXT NOT NULL,
            request_id TEXT,
            source_ip TEXT,
            details_json TEXT
        )"""
    )
    connection.commit()
    return connection


def audit_event(
    *,
    action: str,
    resource: str | None = None,
    outcome: str = "success",
    actor_role: str | None = None,
    request_id: str | None = None,
    source_ip: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    import json

    event_time = datetime.now(timezone.utc).isoformat()
    # Never put API keys, authorization headers, or request bodies into audit details.
    safe_details = details or {}
    with _connection() as connection:
        cursor = connection.execute(
            "INSERT INTO audit_events(event_time,actor_role,action,resource,outcome,request_id,source_ip,details_json) VALUES(?,?,?,?,?,?,?,?)",
            (event_time, actor_role, action, resource, outcome, request_id, source_ip, json.dumps(safe_details, default=str)),
        )
        event_id = int(cursor.lastrowid)
    return {"id": event_id, "event_time": event_time, "action": action, "resource": resource, "outcome": outcome}


def recent_audit_events(limit: int = 50) -> list[dict[str, Any]]:
    import json

    limit = max(1, min(int(limit), 500))
    with _connection() as connection:
        rows = connection.execute(
            "SELECT id,event_time,actor_role,action,resource,outcome,request_id,source_ip,details_json FROM audit_events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        {
            "id": row[0], "event_time": row[1], "actor_role": row[2], "action": row[3],
            "resource": row[4], "outcome": row[5], "request_id": row[6], "source_ip": row[7],
            "details": json.loads(row[8] or "{}"),
        }
        for row in rows
    ]


def security_status() -> dict[str, Any]:
    configured_keys = len(_api_keys())
    return {
        "auth_enabled": auth_enabled(),
        "auth_mode": "api_key" if auth_enabled() else "disabled_demo_mode",
        "configured_roles": sorted({*(_api_keys().values())}),
        "configured_credentials": configured_keys,
        "audit_store": str(AUDIT_DB),
        "secret_source": "environment_or_secret_manager",
        "recommendations": [
            "Enable GOVERNMENT_AUTH_ENABLED in production.",
            "Store credentials in a managed secret store; never commit API keys.",
            "Place the API behind HTTPS, network controls and rate limiting.",
            "Review audit events and retain them according to government policy.",
        ],
    }


def hash_identifier(value: str) -> str:
    """Create a non-reversible identifier for safe correlation in logs."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
