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
        self.assertEqual(result["districts"][0]["geometry_status"], "available")
        self.assertIn("/api/india/district/", result["districts"][0]["climate_metrics_endpoint"])
        svc._joined_districts.cache_clear()


class ParentStateJoinTests(unittest.TestCase):
    """State selection must not silently drop districts."""

    def test_diacritic_state_name_matches_plain_ascii_query(self):
        from backend.services.admin_names import normalise_admin_name

        # geoBoundaries spells this state "Tamil Nādu".
        self.assertEqual(
            normalise_admin_name("Tamil Nādu"), normalise_admin_name("TAMIL NADU")
        )

    def test_state_id_resolves_to_hierarchy_name(self):
        self.assertEqual(svc._resolve_state_name("IN-TN"), "Tamil Nadu")
        self.assertEqual(svc._resolve_state_name("Tamil Nadu"), "Tamil Nadu")

    def test_parent_state_matches_ignores_missing_parent(self):
        self.assertFalse(svc._parent_state_matches({"parent_state": None}, "Kerala"))
        self.assertFalse(svc._parent_state_matches({}, "Kerala"))

    def test_parent_state_matches_accepts_diacritics_and_id(self):
        props = {"parent_state": "Tamil Nādu"}
        self.assertTrue(svc._parent_state_matches(props, "TAMIL NADU"))
        self.assertTrue(svc._parent_state_matches(props, "IN-TN"))
        self.assertFalse(svc._parent_state_matches(props, "Kerala"))

    def test_missing_parent_state_does_not_raise(self):
        """Previous code called .casefold() on a None parent_state."""
        self.assertEqual(svc._parent_state({"parent_state": None}), "")
        self.assertEqual(svc._parent_state({}), "")

    def test_island_district_is_assigned_by_area_not_representative_point(self):
        # A district whose representative point misses its state polygon must
        # still be joined, as happens for Lakshadweep.
        state = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[72, 10], [74, 10], [74, 12], [72, 12], [72, 10]]]},
            "properties": {"shapeName": "Lakshadweep"},
        }
        # Two disjoint islets: the representative point of the pair can fall in
        # open water between them.
        district = {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[72.1, 10.1], [72.2, 10.1], [72.2, 10.2], [72.1, 10.2], [72.1, 10.1]]],
                    [[[73.8, 11.8], [73.9, 11.8], [73.9, 11.9], [73.8, 11.9], [73.8, 11.8]]],
                ],
            },
            "properties": {"shapeName": "Lakshadweep", "shapeID": "IND-D-LAK"},
        }
        with patch.object(svc, "_downloaded") as downloaded:
            downloaded.side_effect = [{"features": [state]}, {"features": [district]}]
            svc._joined_districts.cache_clear()
            joined = svc._joined_districts()
            svc._joined_districts.cache_clear()

        self.assertEqual(len(joined), 1)
        self.assertEqual(joined[0]["properties"]["parent_state"], "Lakshadweep")


class AdminTwinAdapterTests(unittest.TestCase):
    """The generic admin adapter must use installed geometry, not invent it."""

    def test_district_level_falls_back_to_geoboundaries_geometry(self):
        from backend.services import admin_twin_service as admin

        # No india-districts.geojson is installed; the adapter must still find
        # the validated geoBoundaries ADM2 geometry used by the rest of the app.
        self.assertTrue(callable(admin.get_district_geojson))
        with patch.object(admin, "_candidate", return_value=[]), patch.object(
            admin, "get_district_geojson", return_value={"features": [{"type": "Feature", "properties": {"shapeID": "X"}}]}
        ):
            features = admin._features("district")
        self.assertEqual(len(features), 1)

    def test_unknown_admin_id_returns_no_data_without_metrics(self):
        from backend.services import admin_twin_service as admin
        import numpy as np

        with patch.object(admin, "_features", return_value=[]):
            result = admin.build_admin_twin(
                "district", "does-not-exist",
                np.ones((2, 2)), np.array([10.0, 11.0]), np.array([70.0, 71.0]),
                variable="RAINFALL", unit="mm", date="2024-07-15", source="TEST",
            )
        self.assertEqual(result["status"], "no_data")
        self.assertNotIn("state_variables", result)

    def test_aggregation_over_real_polygon_returns_validated_statistics(self):
        from backend.services import admin_twin_service as admin
        import numpy as np

        feature = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [[[70, 10], [72, 10], [72, 12], [70, 12], [70, 10]]]},
            "properties": {"shapeID": "D1"},
        }
        latitudes = np.array([9.0, 10.5, 11.5, 13.0])
        longitudes = np.array([69.0, 71.0, 73.0])
        values = np.arange(12, dtype=float).reshape(4, 3)
        with patch.object(admin, "_features", return_value=[feature]):
            result = admin.build_admin_twin(
                "district", "D1", values, latitudes, longitudes,
                variable="RAINFALL", unit="mm", date="2024-07-15", source="TEST",
            )
        self.assertEqual(result["status"], "available")
        self.assertEqual(result["state_variables"]["valid_grid_cells"], 2)
        self.assertIn("provenance", result)


if __name__ == "__main__":
    unittest.main()
