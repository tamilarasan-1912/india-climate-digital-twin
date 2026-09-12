import json
import os
import unittest
from pathlib import Path


class ApiContractTests(unittest.TestCase):
    def test_source_registry_is_valid_and_india_scoped(self):
        path = Path(__file__).parents[2] / "config" / "source_registry.json"
        registry = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(registry["scope"], "INDIA")
        self.assertFalse(registry["policy"]["fabrication_allowed"])
        self.assertGreater(len(registry["sources"]), 0)
        self.assertTrue(all(source.get("id") and source.get("provider") for source in registry["sources"]))

    def test_api_module_does_not_default_to_wildcard_cors(self):
        previous = os.environ.pop("CORS_ALLOW_ALL", None)
        try:
            import backend.api.main as main
            origins = getattr(main, "_allowed_origins", [])
            self.assertNotIn("*", origins)
            self.assertIn("CORSMiddleware", [middleware.cls.__name__ for middleware in main.app.user_middleware])
            self.assertTrue(callable(getattr(main, "request_context", None)))
        finally:
            if previous is not None:
                os.environ["CORS_ALLOW_ALL"] = previous


if __name__ == "__main__":
    unittest.main()
