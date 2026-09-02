from __future__ import annotations

import unittest
from unittest.mock import patch

from backend.services import twin_engine


class TwinEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.series = [
            {"date": "2024-07-10", "rainfall_mm": 10.0},
            {"date": "2024-07-11", "rainfall_mm": 20.0},
            {"date": "2024-07-12", "rainfall_mm": 30.0},
            {"date": "2024-07-13", "rainfall_mm": 40.0},
            {"date": "2024-07-14", "rainfall_mm": 50.0},
            {"date": "2024-07-15", "rainfall_mm": 60.0},
            {"date": "2024-07-16", "rainfall_mm": 70.0},
        ]
        self.risk = {
            "properties": {
                "risk_distribution": {"low": 1, "moderate": 2, "high": 3, "extreme": 1, "no_data": 0},
                "grid": {"valid_points": 7},
                "statistics": {"mean_hazard_score": 0.4, "maximum_hazard_score": 0.9},
                "maximum_risk": "high",
                "risk_model": "test-risk-model",
            },
            "features": [
                {"properties": {"hazard_score": 0.2}},
                {"properties": {"hazard_score": 0.6}},
                {"properties": {"hazard_score": 0.9}},
            ],
        }

    def test_state_vector_is_complete(self) -> None:
        stats = {"minimum": 10.0, "maximum": 70.0, "mean": 70.0, "median": 70.0}
        vector = twin_engine._state_vector(stats, [10.0, 20.0, 30.0], self.risk)

        self.assertEqual(len(vector), len(twin_engine.STATE_VARIABLES))
        self.assertEqual(vector[0], 70.0)
        self.assertAlmostEqual(vector[6], (0.2 + 0.6 + 0.9) / 3)
        self.assertAlmostEqual(vector[8], 1 / 7)

    @patch.object(twin_engine, "get_dataset_info")
    @patch.object(twin_engine, "get_climate_risk_grid")
    @patch.object(twin_engine, "get_daily_statistics")
    @patch.object(twin_engine, "get_daily_series")
    def test_snapshot_contains_provenance_and_hash(self, get_series, get_stats, get_risk, get_dataset) -> None:
        get_series.return_value = self.series
        get_stats.return_value = {"minimum": 70.0, "maximum": 70.0, "mean": 70.0, "median": 70.0}
        get_risk.return_value = self.risk
        get_dataset.return_value = {"file": "imd_test.nc", "variable": "RAINFALL", "unit": "mm"}

        snapshot = twin_engine.build_twin_snapshot("2024-07-16")

        self.assertEqual(snapshot["twin"]["id"], "india-climate-twin")
        self.assertEqual(snapshot["synchronization"]["observation_date"], "2024-07-16")
        self.assertEqual(snapshot["synchronization"]["source"], "IMD RF25 gridded rainfall")
        self.assertEqual(len(snapshot["state"]["vector"]), 9)
        self.assertRegex(snapshot["synchronization"]["state_hash"], r"^[0-9a-f]{16}$")
        self.assertEqual(snapshot["provenance"]["dataset"]["file"], "imd_test.nc")

    @patch.object(twin_engine, "forecast_next_day", return_value=42.5)
    @patch.object(twin_engine, "get_daily_series")
    def test_what_next_respects_horizon(self, get_series, forecast) -> None:
        get_series.return_value = self.series
        result = twin_engine.build_what_next("2024-07-16", horizon=3)

        self.assertEqual(len(result["forecast"]), 3)
        self.assertEqual(result["forecast"][0]["date"], "2024-07-17")
        self.assertEqual(result["forecast"][-1]["date"], "2024-07-19")
        self.assertEqual(result["forecast"][0]["rainfall_mm"], 42.5)
        forecast.assert_called_once()

    @patch.object(twin_engine, "get_climate_risk_grid")
    def test_what_if_changes_risk_and_records_uncoupled_inputs(self, get_risk) -> None:
        get_risk.return_value = {
            "features": [
                {"properties": {"rainfall_mm": 100.0, "hazard_score": 0.2}},
                {"properties": {"rainfall_mm": 200.0, "hazard_score": 0.4}},
            ],
            "properties": self.risk["properties"],
        }
        result = twin_engine.build_what_if(
            "2024-07-16", precipitation_delta_pct=50.0, temperature_delta_c=2.0,
            sea_level_rise_m=0.5, scenario="test",
        )

        self.assertEqual(result["status"], "scenario_computed")
        self.assertEqual(result["parameters"]["temperature_delta_c"], 2.0)
        self.assertEqual(result["parameters"]["sea_level_rise_m"], 0.5)
        self.assertIn("not coupled", result["coupling"]["temperature"])
        self.assertIn("not coupled", result["coupling"]["sea_level_rise"])
        self.assertNotEqual(result["scenario_result"]["mean_hazard_score"], result["baseline"]["mean_hazard_score"])

    def test_what_if_rejects_invalid_ranges(self) -> None:
        with self.assertRaises(ValueError):
            twin_engine.build_what_if("2024-07-16", precipitation_delta_pct=301)
        with self.assertRaises(ValueError):
            twin_engine.build_what_if("2024-07-16", temperature_delta_c=11)
        with self.assertRaises(ValueError):
            twin_engine.build_what_if("2024-07-16", sea_level_rise_m=2.1)


if __name__ == "__main__":
    unittest.main()
