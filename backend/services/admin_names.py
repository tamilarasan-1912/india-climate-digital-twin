"""Shared administrative-name normalisation for India hierarchy joins.

geoBoundaries ADM1/ADM2 spell states with diacritics and legacy names (e.g.
"Tamil Nādu", "Mahārāshtra") while the platform's hierarchy uses plain ASCII.
Both sides are folded to comparable ASCII before any comparison so that a
state selection is not silently dropped.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalise_admin_name(value: Any) -> str:
    """Fold an administrative name to comparable ASCII."""
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    collapsed = re.sub(r"[^A-Za-z0-9]+", " ", ascii_text).strip().lower()
    return re.sub(r"\s+", " ", collapsed)