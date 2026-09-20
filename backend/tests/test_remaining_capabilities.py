import os
import tempfile
import unittest

from backend.services.alert_service import build_alert
from backend.services.climate_intelligence_service import answer_question
from backend.services.dataset_catalog_store import register_dataset, search_datasets
from backend.services.heat_risk_engine import assess_heat_risk
from backend.services.climate_provider_runtime import get_provider_layer

class RemainingCapabilitiesTest(unittest.TestCase):
    def test_multilingual_alert_marks_review(self):
        result = build_alert(
            hazard="heat", severity="high", region="Tamil Nadu",
            condition="high apparent temperature", action="reduce exposure",
            expires="2026-09-21T00:00:00Z", language="ta"
        )
        self.assertEqual(result["translation_status"], "translation_qa_required")

    def test_catalog_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("CLIMATE_CATALOG_ROOT")
            os.environ["CLIMATE_CATALOG_ROOT"] = tmp
            try:
                record = {"dataset_id": "test-1", "provider": "IMD", "variables": ["precipitation"]}
                register_dataset(record)
                self.assertEqual(search_datasets(provider="IMD")[0]["dataset_id"], "test-1")
            finally:
                if old is None: os.environ.pop("CLIMATE_CATALOG_ROOT", None)
                else: os.environ["CLIMATE_CATALOG_ROOT"] = old

    def test_provider_missing_is_no_data(self):
        os.environ.pop("CLIMATE_PROVIDER_TEMPERATURE_URL", None)
        result = get_provider_layer("temperature", "2026-01-01")
        self.assertEqual(result["status"], "NO_DATA")

    def test_heat_requires_all_components_for_exposure(self):
        result = assess_heat_risk(temperature_c=38, relative_humidity_pct=60)
        self.assertIn(result["status"], {"screening_only", "not_available"})

    def test_intelligence_does_not_fabricate(self):
        result = answer_question("temperature", "2026-01-01", layer="temperature")
        self.assertEqual(result["status"], "NO_DATA")
