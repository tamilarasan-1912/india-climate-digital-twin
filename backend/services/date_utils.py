"""Shared date helpers for time-aware services.

Kept deliberately small: every climate endpoint must distinguish a *malformed*
date (a client error, HTTP 400) from a *well-formed but uncovered* date (a data
availability question, HTTP 200 with an explicit no-data status).
"""
from __future__ import annotations

from datetime import date as date_type


def is_iso_date(value: object) -> bool:
    """True only for a well-formed YYYY-MM-DD calendar date."""
    if not isinstance(value, str):
        return False
    try:
        date_type.fromisoformat(value)
        return True
    except ValueError:
        return False
