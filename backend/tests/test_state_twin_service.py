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


def test_state_stats_accept_plain_lists():
    """Python lists must not be indexed as if they were numpy arrays."""
    result = _stats([1.0, 2.0, 3.0])
    assert result["valid_grid_cells"] == 3
    assert result["maximum_rainfall_mm"] == 3.0


def test_state_metrics_expose_the_keys_the_console_reads():
    """The console renders state metrics by these exact key names.

    A rename here silently falls the state panel back to national values, which
    is a data-integrity failure rather than a cosmetic one, so the contract is
    pinned explicitly.
    """
    from backend.services.state_twin_service import get_state_climate_metrics

    metrics = get_state_climate_metrics("2024-12-31", "IN-TN")["metrics"]

    for key in (
        "valid_grid_cells",
        "mean_rainfall_mm",
        "maximum_rainfall_mm",
        "mean_hazard_score",
        "maximum_hazard_score",
    ):
        assert key in metrics, f"console reads metrics.{key}"


def test_state_twin_state_variables_match_climate_metrics():
    """The twin and climate endpoints must agree for the same state and date."""
    from backend.services.state_twin_service import (
        get_state_climate_metrics,
        get_state_twin,
    )

    date, state_id = "2024-12-31", "IN-TN"
    climate = get_state_climate_metrics(date, state_id)
    twin = get_state_twin(date, state_id)["twin"]["state_variables"]

    assert twin["mean_rainfall_mm"] == climate["metrics"]["mean_rainfall_mm"]
    assert twin["valid_grid_cells"] == climate["metrics"]["valid_grid_cells"]


def test_state_metrics_distinguish_absent_from_malformed_dates():
    from backend.services.state_twin_service import get_state_climate_metrics

    absent = get_state_climate_metrics("1999-01-01", "IN-TN")
    assert absent["status"] == "no_data"
    assert absent["metrics"]["valid_grid_cells"] == 0

    try:
        get_state_climate_metrics("zzz", "IN-TN")
    except ValueError as error:
        assert "ISO-8601" in str(error)
    else:
        raise AssertionError("malformed dates must be rejected as invalid input")


def test_prithvi_contract_matches_official_channel_count():
    from backend.services.prithvi_input_adapter import (
        EXPECTED_VARIABLE_COUNT,
        LEVELS,
        SURFACE_VARIABLES,
        VERTICAL_VARIABLES,
        get_dynamic_channel_names,
    )

    assert len(SURFACE_VARIABLES) == 20
    assert len(VERTICAL_VARIABLES) * len(LEVELS) + len(SURFACE_VARIABLES) == 160
    assert len(get_dynamic_channel_names()) == EXPECTED_VARIABLE_COUNT == 160
    # PRECTOT is not part of the official rollout surface contract.
    assert "PRECTOT" not in SURFACE_VARIABLES


def test_point_timeseries_reports_ocean_cells_explicitly():
    """A land-mask miss must be an explicit status, not a silently null series."""
    from backend.services.forecast_service import get_grid_point_timeseries

    ocean = get_grid_point_timeseries(13.08, 80.27)
    assert ocean["status"] == "no_grid_coverage"
    assert ocean["data_available"] is False
    assert ocean["unavailable_reason"]
    assert ocean["observed_days"] == 0

    inland = get_grid_point_timeseries(28.61, 77.21)
    assert inland["status"] == "available"
    assert inland["data_available"] is True
    assert inland["observed_days"] > 0
    assert inland["unavailable_reason"] is None
