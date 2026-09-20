from backend.services.data_quality_service import validate_array, validate_observation


def test_rainfall_quality_rejects_negative_values():
    result = validate_array([1.0, 2.0, -1.0], variable="rainfall", unit="mm")
    assert result["status"] == "invalid"
    assert "negative_rainfall" in result["issues"]


def test_observation_requires_source_and_variable():
    result = validate_observation({"observation_time": "2026-09-08T00:00:00+00:00"})
    assert result["status"] == "invalid"
