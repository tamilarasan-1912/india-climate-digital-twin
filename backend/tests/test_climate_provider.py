import os
import unittest
from unittest.mock import patch

from backend.services.climate_provider import get_provider_registry, provider_config
from backend.services.climate_provider_runtime import require_http_url


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


class ProviderUrlSchemeTests(unittest.TestCase):
    """A configured provider URL must not become a local-file read primitive."""

    def test_file_scheme_is_rejected(self):
        with self.assertRaises(RuntimeError):
            require_http_url("file:///etc/passwd", context="TEST_URL")

    def test_other_non_http_schemes_are_rejected(self):
        for url in ("ftp://example.invalid/x", "gopher://example.invalid", "data:text/plain,hi"):
            with self.subTest(url=url), self.assertRaises(RuntimeError):
                require_http_url(url, context="TEST_URL")

    def test_http_and_https_are_allowed(self):
        for url in ("http://example.invalid/api", "https://example.invalid/api?x=1"):
            with self.subTest(url=url):
                self.assertEqual(require_http_url(url, context="TEST_URL"), url)

    def test_https_url_without_host_is_rejected(self):
        with self.assertRaises(RuntimeError):
            require_http_url("https:///no-host", context="TEST_URL")

    def test_layer_fetch_refuses_file_url_before_any_io(self):
        from backend.services import climate_provider_runtime as runtime

        with patch.dict(os.environ, {"CLIMATE_PROVIDER_LST_URL": "file:///etc/passwd"}, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                runtime.get_provider_layer("lst", "2024-07-15")
        self.assertIn("http", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
