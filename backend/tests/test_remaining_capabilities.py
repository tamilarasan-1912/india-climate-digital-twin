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

    def test_prithvi_question_reports_real_availability(self):
        """A question about Prithvi-WxC must not report AVAILABLE when blocked.

        Reporting AVAILABLE would light the UI green for a model that cannot run.
        """
        result = answer_question("Is Prithvi-WxC currently available?", "2024-07-15", layer="rainfall")
        from backend.services.prithvi_wxc_service import get_prithvi_wxc_status

        ready = bool(get_prithvi_wxc_status().get("inference_ready"))
        expected = "AVAILABLE" if ready else "BLOCKED"
        self.assertEqual(result["status"], expected)
        self.assertEqual(result["data_available"], ready)
        self.assertEqual(result["inference_ready"], ready)

    def test_state_extreme_rainfall_answer_names_states(self):
        """'Which states had extreme rainfall?' must give a geographic breakdown."""
        result = answer_question("Which states had extreme rainfall?", "2024-07-15", layer="rainfall")
        self.assertEqual(result["status"], "AVAILABLE")
        states = result.get("affected_states")
        self.assertIsInstance(states, list)
        self.assertGreater(len(states), 0)
        threshold = result["threshold_used_mm"]
        for state in states:
            self.assertGreaterEqual(state["maximum_rainfall_mm"], threshold)
            self.assertIn(state["state_name"], result["answer"])
        # Ranking must be descending so the worst-affected state leads.
        maximums = [s["maximum_rainfall_mm"] for s in states]
        self.assertEqual(maximums, sorted(maximums, reverse=True))

    def test_provider_layer_preserves_declared_provenance(self):
        """A reachable provider's own identity must survive into provenance.

        The adapter must not replace the source it actually queried with a
        generic placeholder, which would make provenance untraceable.
        """
        import json
        from http.server import BaseHTTPRequestHandler, HTTPServer
        import threading

        payload = {
            "status": "AVAILABLE",
            "data_available": True,
            "features": [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [78.0, 12.0]},
                          "properties": {"temperature_c": 31.4}}],
            "provider": "imd-temperature-endpoint",
            "provenance": {"provider": "imd-temperature-endpoint", "dataset": "IMD-TEMP-2024",
                           "variable": "temperature", "units": "degC",
                           "retrieved_at": "2026-09-20T00:00:00Z"},
        }

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old = os.environ.get("CLIMATE_PROVIDER_TEMPERATURE_URL")
        try:
            os.environ["CLIMATE_PROVIDER_TEMPERATURE_URL"] = (
                f"http://127.0.0.1:{server.server_port}/temperature"
            )
            result = get_provider_layer("temperature", "2024-07-15")
            self.assertEqual(result["status"], "AVAILABLE")
            self.assertEqual(result["provider"], "imd-temperature-endpoint")
            self.assertEqual(result["provenance"]["provider"], "imd-temperature-endpoint")
            self.assertEqual(result["provenance"]["dataset"], "IMD-TEMP-2024")
            self.assertEqual(result["provenance"]["units"], "degC")
        finally:
            server.shutdown()
            server.server_close()
            if old is None:
                os.environ.pop("CLIMATE_PROVIDER_TEMPERATURE_URL", None)
            else:
                os.environ["CLIMATE_PROVIDER_TEMPERATURE_URL"] = old

    def test_provider_layer_requires_configured_url(self):
        old = os.environ.pop("CLIMATE_PROVIDER_SST_URL", None)
        try:
            result = get_provider_layer("sst", "2024-07-15")
            self.assertEqual(result["status"], "NO_DATA")
            self.assertFalse(result["data_available"])
            self.assertEqual(result["env_var"], "CLIMATE_PROVIDER_SST_URL")
        finally:
            if old is not None:
                os.environ["CLIMATE_PROVIDER_SST_URL"] = old

    def test_provider_layer_rejects_non_object_payload(self):
        """A provider returning a JSON array must fail loudly, not be coerced."""
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                body = b"[1, 2, 3]"
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        old = os.environ.get("CLIMATE_PROVIDER_ANOMALIES_URL")
        try:
            os.environ["CLIMATE_PROVIDER_ANOMALIES_URL"] = (
                f"http://127.0.0.1:{server.server_port}/anomalies"
            )
            with self.assertRaises(RuntimeError):
                get_provider_layer("anomalies", "2024-07-15")
        finally:
            server.shutdown()
            server.server_close()
            if old is None:
                os.environ.pop("CLIMATE_PROVIDER_ANOMALIES_URL", None)
            else:
                os.environ["CLIMATE_PROVIDER_ANOMALIES_URL"] = old


class DistrictAssistantTest(unittest.TestCase):
    """Districts must be answerable from real aggregated observations."""

    DATE = "2024-07-15"

    def test_district_question_returns_real_aggregation(self):
        from backend.services.climate_intelligence_service import answer_question

        answer = answer_question("What was rainfall in Coimbatore district on this date?", self.DATE)
        self.assertEqual(answer["status"], "AVAILABLE")
        self.assertTrue(answer["data_available"])
        self.assertEqual(answer["district_name"], "Coimbatore")
        self.assertEqual(answer["state"], "Tamil Nadu")
        self.assertGreater(answer["metrics"]["valid_grid_cells"], 0)
        # The district maximum must be a real grid value, not an estimate.
        self.assertGreaterEqual(
            answer["metrics"]["maximum_rainfall_mm"], answer["metrics"]["mean_rainfall_mm"]
        )

    def test_district_question_is_backed_by_imd(self):
        from backend.services.climate_intelligence_service import answer_question

        answer = answer_question("rainfall in North Goa", self.DATE)
        self.assertEqual(answer["status"], "AVAILABLE")
        self.assertEqual(answer["source"], "IMD")
        self.assertIn("provenance", answer)

    def test_uncovered_district_reports_no_data_not_a_value(self):
        from backend.services.climate_intelligence_service import answer_question
        from backend.services.district_climate_service import (
            _normalised_districts,
            get_district_climate_metrics,
        )

        # Find a district that genuinely has no IMD grid-point centre.
        uncovered = None
        for district_id, _name, _state, _geom in _normalised_districts():
            metrics = get_district_climate_metrics(self.DATE, district_id)
            if metrics["status"] != "available":
                uncovered = metrics["district_name"]
                break
        self.assertIsNotNone(uncovered, "expected at least one district without grid coverage")

        answer = answer_question(f"rainfall in {uncovered} district", self.DATE)
        self.assertEqual(answer["status"], "NO_DATA")
        self.assertFalse(answer["data_available"])
        self.assertNotIn("metrics", answer)

    def test_word_boundary_matching_avoids_false_district_hits(self):
        from backend.services.climate_intelligence_service import _district_mentioned

        # "Una" is a real district name; "unavailable" must not match it.
        self.assertIsNone(_district_mentioned("Why is temperature unavailable?"))
        self.assertIsNone(_district_mentioned("What is the current climate state?"))

    def test_longest_district_name_wins(self):
        from backend.services.climate_intelligence_service import _district_mentioned
        from backend.services.district_climate_service import get_district_climate_metrics

        match = _district_mentioned("rainfall in North Goa district")
        self.assertIsNotNone(match)
        self.assertEqual(
            get_district_climate_metrics(self.DATE, match)["district_name"], "North Goa"
        )

    def test_assistant_capabilities_include_districts(self):
        from backend.services.climate_intelligence_service import get_intelligence_capabilities

        intents = get_intelligence_capabilities()["supported_intents"]
        self.assertIn("district-level rainfall aggregation", intents)
