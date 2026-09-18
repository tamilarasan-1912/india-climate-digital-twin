import unittest
from unittest.mock import patch

from backend.services.gods_eye_operations_service import (
    build_gods_eye_events,
    build_gods_eye_operations,
    build_gods_eye_timeline,
)


class GodsEyeOperationsTests(unittest.TestCase):
    @patch("backend.services.gods_eye_operations_service.get_baseline_forecast")
    @patch("backend.services.gods_eye_operations_service.get_historical_rainfall")
    def test_timeline_contract(self, historical, forecast):
        historical.return_value = {"provider": "IMD", "unit": "mm", "count": 1, "series": [{"date": "2024-07-15", "rainfall_mm": 12.0}]}
        forecast.return_value = {"status": "baseline", "forecast": [{"date": "2024-07-16", "rainfall_mm": 10.0}]}
        result = build_gods_eye_timeline("2024-07-15", "2024-07-15", 1)
        self.assertEqual(result["contract"], "india-climate-timeline/v1")
        self.assertEqual(result["history"]["provider"], "IMD")
        self.assertEqual(len(result["forecast"]["forecast"]), 1)

    @patch("backend.services.gods_eye_operations_service.get_extreme_event_summary")
    @patch("backend.services.gods_eye_operations_service.get_extreme_rainfall_geojson")
    def test_event_objects(self, geojson, summary):
        geojson.return_value = {"features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [80, 13]}, "properties": {"rainfall_mm": 120, "category": "very_heavy"}}]}
        summary.return_value = {"summary": {"total_extreme_points": 1}}
        result = build_gods_eye_events("2024-07-15")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["events"][0]["type"], "extreme_rainfall")

    @patch("backend.services.gods_eye_operations_service.get_layer_status")
    @patch("backend.services.gods_eye_operations_service.get_climate_layer_catalog")
    def test_operations_expose_no_data_without_fabrication(self, catalog, status):
        catalog.return_value = {"layers": {"temperature": {"title": "Temperature", "providers": ["IMD"]}}}
        status.return_value = {"status": "NO_DATA", "data_available": False}
        result = build_gods_eye_operations("2024-07-15")
        self.assertEqual(result["layers"][0]["status"], "NO_DATA")
        self.assertIsNone(result["layers"][0]["observation_time"])


if __name__ == "__main__":
    unittest.main()
