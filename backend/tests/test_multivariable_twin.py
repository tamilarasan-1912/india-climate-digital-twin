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
