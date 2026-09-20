from backend.services.operations_service import get_operations_status


def test_operations_status_is_india_scoped_and_non_synthetic():
    result = get_operations_status()
    assert result["scope"] == "India"
    assert result["forecast"]["synthetic_forecast"] is False
    assert "connected_sources" in result["data"]
    assert "operator_actions" in result
