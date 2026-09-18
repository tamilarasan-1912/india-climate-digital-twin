import unittest

from backend.services.climate_layer_service import get_climate_layer_catalog, get_layer_status, unavailable_layer


class ClimateLayerTests(unittest.TestCase):
    def test_catalog_is_explicit_about_provider_status(self):
        catalog = get_climate_layer_catalog()
        self.assertEqual(catalog["scope"], "India")
        self.assertEqual(catalog["layers"]["rainfall"]["status"], "connected")
        self.assertEqual(catalog["layers"]["temperature"]["status"], "provider_required")
        self.assertEqual(catalog["layers"]["lst"]["status"], "provider_required")
        self.assertEqual(catalog["layers"]["sst"]["status"], "provider_required")

    def test_unavailable_layer_never_returns_synthetic_values(self):
        result = unavailable_layer("temperature", "2026-09-19")
        self.assertEqual(result["status"], "NO_DATA")
        self.assertFalse(result["data_available"])
        self.assertEqual(result["features"], [])

    def test_layer_status_keeps_provider_provenance(self):
        result = get_layer_status("lst", "2026-09-19")
        self.assertEqual(result["providers"], ["ISRO/MOSDAC", "MODIS", "Landsat"])
        self.assertFalse(result["data_available"])


if __name__ == "__main__":
    unittest.main()
