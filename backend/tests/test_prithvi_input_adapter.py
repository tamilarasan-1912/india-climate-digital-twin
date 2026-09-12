"""Tests for the canonical Prithvi WxC input contract."""

from datetime import datetime, timedelta

from backend.services.prithvi_input_adapter import (
    EXPECTED_VARIABLE_COUNT,
    FORECAST_LEAD_HOURS,
    INPUT_INTERVAL_HOURS,
    get_dynamic_channel_names,
    validate_current_imd_dataset,
    validate_dataset_metadata,
    validate_tensor_shape,
)


def test_canonical_contract_has_160_channels():
    channels = get_dynamic_channel_names()
    assert len(channels) == EXPECTED_VARIABLE_COUNT == 160
    assert len(set(channels)) == 160


def test_current_imd_dataset_is_rejected():
    result = validate_current_imd_dataset()
    assert result["prithvi_compatible"] is False
    assert result["validation"]["supplied_variable_count"] == 1


def test_tensor_contract():
    assert validate_tensor_shape([1, 2, 160, 64, 128])["valid"] is True
    assert validate_tensor_shape([1, 1, 160, 64, 128])["valid"] is False
    assert validate_tensor_shape([1, 2, 159, 64, 128])["valid"] is False


def test_timestamp_interval_is_six_hours():
    channels = get_dynamic_channel_names()
    units = {name.split("@")[0]: "" for name in channels}
    now = datetime(2026, 1, 1, 0, 0)
    result = validate_dataset_metadata(
        variables=channels,
        timestamps=[now, now + timedelta(hours=INPUT_INTERVAL_HOURS)],
        latitudes=[-90.0, 0.0, 90.0],
        longitudes=[0.0, 180.0],
        units=units,
    )
    # Empty-unit variables are valid, but variables with defined units must
    # still provide their canonical unit metadata.
    assert result["valid"] is False
    assert result["required_input_interval_hours"] == 6
    assert result["required_forecast_lead_hours"] == FORECAST_LEAD_HOURS
