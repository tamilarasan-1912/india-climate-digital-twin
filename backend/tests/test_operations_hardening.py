from backend.services.operations_hardening_service import request_id, security_headers


def test_request_id_accepts_safe_existing_value():
    assert request_id("abc-123_ok").startswith("abc-123_ok")


def test_request_id_replaces_unsafe_or_oversized_value():
    value = request_id("bad value")
    assert value and value != "bad value"


def test_security_headers_are_conservative():
    headers = security_headers()
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert headers["Cache-Control"] == "no-store"
