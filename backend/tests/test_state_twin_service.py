from backend.services.state_twin_service import _stats


def test_state_stats_are_deterministic():
    result = _stats([1.0, 64.5, 115.6, 204.5])
    assert result["valid_grid_cells"] == 4
    assert result["mean_rainfall_mm"] == 96.4
    assert result["median_rainfall_mm"] == 90.05
    assert result["maximum_rainfall_mm"] == 204.5
    assert 0 <= result["mean_hazard_score"] <= 100
    assert result["risk_category"] in {"low", "moderate", "high", "extreme"}


def test_state_stats_handle_no_data():
    result = _stats([float("nan"), float("nan")])
    assert result["valid_grid_cells"] == 0
    assert result["mean_rainfall_mm"] is None
    assert result["risk_category"] == "no_data"
