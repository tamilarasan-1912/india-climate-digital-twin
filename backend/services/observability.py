"""Lightweight structured observability primitives.

Logs are structured JSON with a request identifier so a single request can be
traced across services. Secrets, credentials and request bodies are never
logged.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="")

_ACCESS_LOGGER = logging.getLogger("climate.access")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.time(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        return json.dumps(payload, separators=(",", ":"))


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def new_request_id() -> str:
    return uuid.uuid4().hex


def log_request(*, endpoint: str, status: int, duration_ms: float, method: str = "GET") -> None:
    """Emit one structured access record per request.

    Never includes headers, credentials or request bodies.
    """
    _ACCESS_LOGGER.info(
        json.dumps(
            {
                "timestamp": time.time(),
                "request_id": request_id_var.get(),
                "endpoint": endpoint,
                "method": method,
                "status": status,
                "duration_ms": round(duration_ms, 3),
            },
            separators=(",", ":"),
        )
    )