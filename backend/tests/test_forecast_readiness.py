from backend.services.forecast_readiness_service import assess_prithvi_readiness


def test_prithvi_is_blocked_without_full_contract():
    result = assess_prithvi_readiness({"valid": False, "variable_count": 12})
    assert result["status"] == "blocked"
    assert result["synthetic_forecast_allowed"] is False


def test_prithvi_ready_when_contract_is_valid():
    result = assess_prithvi_readiness({"valid": True, "variable_count": 160})
    assert result["status"] == "ready"
