from backend.services.assimilation_service import assimilate_variable
from backend.services.multi_hazard_service import calculate_hazards


def test_assimilation_fuses_sources_and_reports_uncertainty():
    result = assimilate_variable([
        {"source": "obs", "value": 10.0, "weight": 2},
        {"source": "reanalysis", "value": 14.0, "weight": 1},
    ])
    assert result["status"] == "assimilated"
    assert 10 < result["value"] < 14
    assert result["uncertainty"] > 0


def test_multihazard_does_not_invent_missing_temperature():
    state = {"twin_state": {"variables": {"rainfall": {"statistics": {"mean": 100.0}}}}}
    result = calculate_hazards(state)
    assert result["hazards"]["extreme_rainfall"]["status"] == "available"
    assert result["hazards"]["heat"]["status"] == "no_data"


def test_active_variable_catalog_excludes_blocked_sources():
    """Atmospheric variables must not be advertised while Prithvi is blocked."""
    from backend.services.multi_variable_twin_service import get_active_variable_catalog

    active = {item["id"]: item for item in get_active_variable_catalog()}
    assert "precipitation" in active
    assert active["precipitation"]["availability"] == "available"
    assert "air_temperature_2m" not in active
    assert "wind_u_10m" not in active


def test_variable_report_marks_blocked_sources_explicitly():
    from backend.services.multi_variable_twin_service import get_variable_availability_report

    report = get_variable_availability_report()
    by_id = {item["id"]: item for item in report["variables"]}
    assert by_id["air_temperature_2m"]["availability"] == "blocked"
    assert by_id["relative_humidity"]["availability"] == "planned"
    assert "air_temperature_2m" in report["unavailable_variables"]


def test_active_variable_catalog_marks_every_entry_available():
    from backend.services.multi_variable_twin_service import get_active_variable_catalog

    for item in get_active_variable_catalog():
        assert item["availability"] == "available", item["id"]


def test_climate_state_reports_connected_rainfall_source():
    """The operational IMD dataset must be discovered by the multi-variable state."""
    from backend.services.climate_state_service import discover_variable

    registry = discover_variable("rainfall")
    assert registry["status"] == "available"
    files = [match["file"] for match in registry["matches"] if "variable" in match]
    assert any("RF25" in path for path in files), files


def test_climate_state_missing_variables_stay_missing():
    from backend.services.climate_state_service import build_climate_state

    state = build_climate_state("2024-07-15")["twin_state"]
    assert "rainfall" in state["available_variables"]
    for variable in ("temperature", "wind", "humidity"):
        assert variable in state["missing_variables"]
        assert state["variables"][variable]["status"] == "no_data"


def test_climate_state_does_not_substitute_a_nearby_date():
    """An out-of-coverage date must be no_data, never a nearest-day value."""
    from backend.services.climate_state_service import _read_variable

    result = _read_variable("rainfall", "1999-01-01")
    assert result["status"] == "no_data"
    assert result["quality_flag"] == "date_not_in_dataset"
    assert result["coverage"]["start"] <= result["coverage"]["end"]


def test_climate_state_discovery_requires_a_usable_variable():
    from backend.services.climate_state_service import discover_variable

    registry = discover_variable("humidity")
    usable = [match for match in registry["matches"] if "variable" in match]
    if not usable:
        assert registry["status"] == "no_data"
