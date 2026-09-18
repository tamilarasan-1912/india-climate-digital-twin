import unittest
from unittest.mock import patch

from backend.services import administrative_boundary_service as svc


class AdministrativeBoundaryTests(unittest.TestCase):
    @patch.object(svc, "_downloaded")
    def test_districts_are_exposed_without_climate_values(self, downloaded):
        downloaded.side_effect = [
            {"features": [
                {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[77, 12], [78, 12], [78, 13], [77, 12]]]}, "properties": {"shapeName": "Tamil Nadu"}}
            ]},
            {"features": [
                {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[77.1, 12.1], [77.2, 12.1], [77.2, 12.2], [77.1, 12.1]]]}, "properties": {"shapeName": "Test District", "shapeID": "IND-D-1"}}
            ]},
        ]
        svc._joined_districts.cache_clear()
        result = svc.get_districts("Tamil Nadu")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["districts"][0]["name"], "Test District")
        self.assertEqual(result["districts"][0]["data_status"], "geometry_available_climate_metrics_provider_required")
        svc._joined_districts.cache_clear()


if __name__ == "__main__":
    unittest.main()
