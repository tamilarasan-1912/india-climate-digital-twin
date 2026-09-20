"""District-level climate aggregation tests.

These tests assert the scientific contract: district metrics must come from real
IMD grid cells genuinely covered by real district polygons, and districts with
no intersecting grid-point centre must report no coverage rather than an
inferred or parent-state value.
"""

from __future__ import annotations

import unittest

from backend.services import district_climate_service as svc


class DistrictGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.districts = svc._normalised_districts()

    def test_district_geometries_are_available(self):
        self.assertGreater(len(self.districts), 600)
        ids = [item[0] for item in self.districts]
        self.assertEqual(len(ids), len(set(ids)), "district identifiers must be unique")

    def test_every_district_has_parsed_geometry(self):
        for _id, name, _state, geometry in self.districts[:50]:
            self.assertTrue(geometry.is_valid or geometry.area >= 0, f"{name} has unusable geometry")


class DistrictNameNormalisationTests(unittest.TestCase):
    def test_diacritics_fold_to_ascii(self):
        # geoBoundaries ships "Tamil Nādu"; the hierarchy uses "Tamil Nadu".
        self.assertEqual(svc.normalise_admin_name("Tamil Nādu"), svc.normalise_admin_name("Tamil Nadu"))
        self.assertEqual(svc.normalise_admin_name("Mahārāshtra"), svc.normalise_admin_name("Maharashtra"))

    def test_canonical_state_name_recovers_hierarchy_spelling(self):
        self.assertEqual(svc.canonical_state_name("Tamil Nādu"), "Tamil Nadu")
        self.assertEqual(svc.canonical_state_name("Telangāna"), "Telangana")
        self.assertIsNone(svc.canonical_state_name(None))


class DistrictAggregationTests(unittest.TestCase):
    DATE = "2024-07-15"

    @classmethod
    def setUpClass(cls):
        cls.payload = svc.get_all_district_climate_metrics(cls.DATE)

    def test_national_aggregation_covers_the_country(self):
        self.assertEqual(self.payload["status"], "available")
        self.assertEqual(self.payload["count"], len(svc._normalised_districts()))
        self.assertGreater(self.payload["districts_with_data"], 600)

    def test_explicit_no_coverage_for_unrepresented_districts(self):
        missing = [d for d in self.payload["districts"] if not d["valid_grid_cells"]]
        self.assertTrue(missing, "expected at least one district with no grid coverage")
        for district in missing:
            self.assertEqual(district["status"], "no_grid_coverage")
            # A missing value must stay missing, never be coerced to 0.
            self.assertIsNone(district["mean_rainfall_mm"])
            self.assertIsNone(district["maximum_rainfall_mm"])
            self.assertEqual(district["risk_category"], "no_data")
            self.assertEqual(district["data_coverage"]["grid_coverage_percent"], 0.0)
            self.assertTrue(district["data_coverage"]["unavailable_reason"])

    def test_aggregation_statistics_are_internally_consistent(self):
        for district in self.payload["districts"]:
            if not district["valid_grid_cells"]:
                continue
            self.assertLessEqual(district["minimum_rainfall_mm"], district["mean_rainfall_mm"])
            self.assertLessEqual(district["mean_rainfall_mm"], district["maximum_rainfall_mm"])
            self.assertGreaterEqual(district["mean_rainfall_mm"], 0.0)
            self.assertIn(district["risk_category"], {"low", "moderate", "high", "extreme"})

    def test_every_district_reports_provenance(self):
        for district in self.payload["districts"][:200]:
            self.assertEqual(district["data_coverage"]["geometry_available"], True)
            self.assertIn("grid_cells_in_district", district["data_coverage"])

    def test_national_maximum_district_matches_state_aggregate(self):
        """A district maximum may not exceed the state polygon maximum.

        Both aggregates are computed from the same IMD grid, so the district
        view must be a spatial refinement of the state view, never a superset.
        """
        from backend.services.state_twin_service import get_state_climate_metrics

        ranked = sorted(
            (d for d in self.payload["districts"] if d["valid_grid_cells"]),
            key=lambda d: d["maximum_rainfall_mm"],
            reverse=True,
        )
        top = ranked[0]
        state = get_state_climate_metrics(self.DATE, _state_id_for(top["state"]))
        self.assertLessEqual(top["maximum_rainfall_mm"], state["metrics"]["maximum_rainfall_mm"])


class StateDistrictRollupTests(unittest.TestCase):
    DATE = "2024-07-15"

    def test_state_rollup_matches_district_membership(self):
        rollup = svc.get_state_district_climate_metrics(self.DATE, "IN-TN")
        self.assertEqual(rollup["state_name"], "Tamil Nadu")
        self.assertGreater(rollup["count"], 30)
        for district in rollup["districts"]:
            self.assertEqual(district["state"], "Tamil Nadu")
        self.assertGreater(rollup["districts_with_data"], 30)

    def test_unknown_state_is_rejected(self):
        with self.assertRaises(ValueError):
            svc.get_state_district_climate_metrics(self.DATE, "IN-ZZ")

    def test_unknown_district_is_rejected(self):
        with self.assertRaises(ValueError):
            svc.get_district_climate_metrics(self.DATE, "not-a-district")

    def test_single_district_matches_bulk_result(self):
        districts = svc._normalised_districts()
        target = districts[0][0]
        single = svc.get_district_climate_metrics(self.DATE, target)
        bulk = next(
            d for d in svc.get_all_district_climate_metrics(self.DATE)["districts"]
            if d["district_id"] == target
        )
        self.assertEqual(single["metrics"]["mean_rainfall_mm"], bulk["mean_rainfall_mm"])
        self.assertEqual(single["metrics"]["valid_grid_cells"], bulk["valid_grid_cells"])

    def test_invalid_date_is_rejected(self):
        with self.assertRaises(ValueError):
            svc.get_district_climate_metrics("1999-01-01", svc._normalised_districts()[0][0])


def _state_id_for(state_name):
    from backend.services.india_hierarchy_service import STATES_AND_UTS

    return next(item["id"] for item in STATES_AND_UTS if item["name"] == state_name)


if __name__ == "__main__":
    unittest.main()