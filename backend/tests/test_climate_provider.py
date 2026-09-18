import os
import unittest
from unittest.mock import patch

from backend.services.climate_provider import get_provider_registry, provider_config


class ClimateProviderTests(unittest.TestCase):
    def test_unconfigured_provider_is_explicit(self):
        with patch.dict(os.environ, {}, clear=True):
            result = provider_config("temperature")
        self.assertEqual(result["status"], "provider_required")
        self.assertFalse(result["configured"])

    def test_configuration_does_not_claim_connected_data(self):
        with patch.dict(os.environ, {"CLIMATE_PROVIDER_LST_URL": "https://example.invalid/lst"}, clear=True):
            result = provider_config("lst")
        self.assertEqual(result["status"], "configured")
        self.assertTrue(result["configured"])
        self.assertIn("validated by a source-specific adapter", result["note"])

    def test_registry_contains_target_layers(self):
        with patch.dict(os.environ, {}, clear=True):
            registry = get_provider_registry()
        self.assertEqual(
            set(registry["providers"]),
            {"rainfall", "temperature", "lst", "sst", "anomalies"},
        )


if __name__ == "__main__":
    unittest.main()
