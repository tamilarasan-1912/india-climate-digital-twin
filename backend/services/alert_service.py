"""Multilingual early-warning message generation.

This module creates channel-neutral alert payloads. Delivery (SMS, push,
WhatsApp, email, siren/IoT) is intentionally separated from message
construction so providers can be swapped without changing scientific logic.
"""
from __future__ import annotations

from typing import Any

SUPPORTED_LANGUAGES = {
    "en": "English", "hi": "हिन्दी", "bn": "বাংলা", "te": "తెలుగు",
    "mr": "मराठी", "ta": "தமிழ்", "gu": "ગુજરાતી", "kn": "ಕನ್ನಡ",
    "ml": "മലയാളം", "or": "ଓଡ଼ିଆ", "pa": "ਪੰਜਾਬੀ", "as": "অসমীয়া",
}

# Operational systems must pass these through linguistic/domain QA before public
# deployment. English is the reference message; other locales are structured
# extension points rather than claims of government-approved translations.
REFERENCE_TEMPLATE = (
    "{severity} {hazard} alert for {region}. "
    "Expected condition: {condition}. Valid until {expires}. "
    "Recommended action: {action}."
)


def build_alert(
    *,
    hazard: str,
    severity: str,
    region: str,
    condition: str,
    action: str,
    expires: str,
    language: str = "en",
    alert_id: str | None = None,
) -> dict[str, Any]:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language '{language}'")
    message = REFERENCE_TEMPLATE.format(
        severity=severity,
        hazard=hazard,
        region=region,
        condition=condition,
        expires=expires,
        action=action,
    )
    return {
        "alert_id": alert_id,
        "hazard": hazard,
        "severity": severity,
        "language": language,
        "language_name": SUPPORTED_LANGUAGES[language],
        "title": f"{severity} {hazard} alert",
        "message": message,
        "region": region,
        "delivery_status": "not_dispatched",
        "acknowledgement_required": severity.lower() in {"high", "severe", "critical"},
        "translation_status": "reference_template" if language == "en" else "translation_qa_required",
        "scientific_status": "message generation only; alert issuance requires a validated hazard rule and operational authority",
    }


def get_language_catalog() -> list[dict[str, str]]:
    return [
        {"code": code, "name": name, "status": "reference" if code == "en" else "qa_required"}
        for code, name in SUPPORTED_LANGUAGES.items()
    ]
