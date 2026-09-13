import unittest

from backend.services.alert_service import build_alert
from backend.services.risk_engine import assess_asset, expected_annual_loss
from backend.services.scenario_engine import build_scenario


class IndustryPlatformTests(unittest.TestCase):
    def test_missing_risk_component_is_not_zero(self):
        result = assess_asset(
            asset_id="asset-1",
            location_id="loc-1",
            hazard="heat",
            hazard_value=0.8,
            exposure_value=None,
            vulnerability_value=0.5,
            confidence=0.7,
            assessment_time="2026-01-01T00:00:00Z",
            model_version="test",
        )
        self.assertIsNone(result["risk"]["score"])
        self.assertEqual(result["status"], "not_available")

    def test_expected_annual_loss(self):
        self.assertEqual(expected_annual_loss(0.1, 1_000_000, 0.5), 50_000)

    def test_scenario_marks_coastal_as_uncoupled(self):
        result = build_scenario(
            scenario_id="s1",
            name="2050 test",
            horizon_year=2050,
            sea_level_rise_m=0.5,
        )
        self.assertIn("coastal_inundation", result["uncoupled_parameters"])
        self.assertFalse(result["physical_simulation_available"])

    def test_alert_language_catalog_contract(self):
        result = build_alert(
            hazard="heat",
            severity="High",
            region="Chennai",
            condition="temperature above threshold",
            action="reduce outdoor exposure",
            expires="2026-06-01T18:00:00Z",
            language="ta",
        )
        self.assertEqual(result["language"], "ta")
        self.assertEqual(result["translation_status"], "translation_qa_required")


if __name__ == "__main__":
    unittest.main()
