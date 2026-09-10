from __future__ import annotations

from backend.services import governance_service as governance


def test_roles_have_expected_permissions():
    assert governance.can("administrator", "manage")
    assert governance.can("national_operator", "operate")
    assert governance.can("analyst", "analyse")
    assert governance.can("viewer", "read")
    assert not governance.can("viewer", "manage")


def test_authentication_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("GOVERNMENT_AUTH_ENABLED", raising=False)
    identity = governance.authenticate(None)
    assert identity["auth_mode"] == "disabled"
    assert identity["role"] == "system_demo"


def test_configured_api_key_maps_to_role(monkeypatch):
    monkeypatch.setenv("GOVERNMENT_AUTH_ENABLED", "true")
    monkeypatch.setenv("GOVERNMENT_API_KEYS", "analyst:test-secret")
    identity = governance.authenticate("test-secret")
    assert identity == {"authenticated": True, "role": "analyst", "auth_mode": "api_key"}
    assert not governance.authenticate("wrong-secret")["authenticated"]
