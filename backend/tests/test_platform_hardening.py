"""Tests for dataset lifecycle safety, catalog, security and status truthfulness."""
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

from backend.services.auth_service import operator_auth_status, require_operator
from backend.services.climate_intelligence_service import (
    answer_question,
    NO_DATA_MESSAGE,
    get_intelligence_capabilities,
)
from backend.services.dataset_catalog_store import (
    catalog_summary,
    delete_dataset,
    get_dataset,
    load_catalog,
    register_dataset,
    search_datasets,
)
from backend.services.model_registry import get_model_registry
from backend.services.rainfall_service import (
    get_daily_statistics,
    get_india_daily_summary,
    read_dataset,
)


class RainfallSummaryContractTests(unittest.TestCase):
    """The console reads `rainfall.mean_mm`; guard that field name in CI."""

    DATE = "2024-07-15"

    def test_summary_exposes_nested_rainfall_mm_fields(self):
        summary = get_india_daily_summary(self.DATE)
        rainfall = summary.get("rainfall")
        self.assertIsInstance(rainfall, dict)
        for field in ("mean_mm", "maximum_mm", "minimum_mm", "median_mm"):
            self.assertIn(field, rainfall)
            self.assertIsInstance(rainfall[field], (int, float))
        self.assertIn("grid_points", summary)


class RiskConsistencyValidationTests(unittest.TestCase):
    """The validation endpoint must report structured, truthful results."""

    def test_validation_report_is_structured_and_passing(self):
        from backend.services.validation_service import validate_risk_grid

        report = validate_risk_grid()
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["checks_passed"], report["checks_total"])
        self.assertGreater(report["checks_total"], 0)
        for check in report["checks"]:
            self.assertIn("check", check)
            self.assertIsInstance(check["passed"], bool)

    def test_validation_declares_its_limits(self):
        from backend.services.validation_service import validate_risk_grid

        report = validate_risk_grid()
        self.assertEqual(report["validation_type"], "internal_consistency")
        self.assertTrue(report["limitations"])

    def test_unavailable_date_surfaces_as_an_error_not_a_pass(self):
        from backend.services.validation_service import validate_risk_grid

        with self.assertRaises(ValueError):
            validate_risk_grid("1999-01-01")


class ClimateStateDiscoveryTests(unittest.TestCase):
    def test_imd_dataset_is_reachable_from_the_shared_data_roots(self):
        from backend.services.climate_state_service import DATA_ROOTS

        self.assertTrue(any(root.exists() for root in DATA_ROOTS), DATA_ROOTS)


class DatasetLifecycleTests(unittest.TestCase):
    def test_repeated_and_concurrent_reads_share_the_cached_dataset(self):
        first = get_daily_statistics("2024-07-15")

        def read(_):
            return get_daily_statistics("2024-07-15")["grid_points"]

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(read, range(32)))

        self.assertTrue(all(count > 0 for count in results))
        # A closed cache would raise here; the values must also stay identical.
        self.assertEqual(get_daily_statistics("2024-07-15"), first)

    def test_read_dataset_is_a_locked_context_manager(self):
        with read_dataset() as dataset:
            self.assertIn("RAINFALL", dataset)
        with read_dataset() as dataset:
            self.assertIn("TIME", dataset)


class CatalogContractTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._old = os.environ.get("CLIMATE_CATALOG_ROOT")
        os.environ["CLIMATE_CATALOG_ROOT"] = self._tmp.name

    def tearDown(self):
        if self._old is None:
            os.environ.pop("CLIMATE_CATALOG_ROOT", None)
        else:
            os.environ["CLIMATE_CATALOG_ROOT"] = self._old
        self._tmp.cleanup()

    def test_register_search_and_lineage(self):
        register_dataset({
            "dataset_id": "imd-test",
            "provider": "IMD",
            "variables": ["precipitation"],
            "validation_status": "validated",
            "derived_from": ["raw-imd"],
            "processing": "gridded_to_point_geojson",
        })
        register_dataset({"dataset_id": "era5-test", "provider": "ERA5", "variables": ["temperature"]})

        self.assertEqual(len(search_datasets()), 2)
        self.assertEqual(len(search_datasets(provider="imd")), 1)
        self.assertEqual(len(search_datasets(variable="temperature")), 1)
        self.assertEqual(len(search_datasets(validation_status="validated")), 1)
        self.assertEqual(len(search_datasets(text="precipitation")), 1)

        record = get_dataset("imd-test")
        self.assertEqual(record["lineage"]["derived_from"], ["raw-imd"])
        self.assertEqual(record["lineage"]["processing"], "gridded_to_point_geojson")

    def test_register_is_idempotent_and_delete_reports_missing(self):
        register_dataset({"dataset_id": "dup", "provider": "IMD"})
        register_dataset({"dataset_id": "dup", "provider": "IMD", "variables": ["x"]})
        self.assertEqual(len(search_datasets()), 1)
        self.assertTrue(delete_dataset("dup"))
        self.assertFalse(delete_dataset("dup"))

    def test_missing_required_fields_rejected(self):
        with self.assertRaises(ValueError):
            register_dataset({"provider": "IMD"})
        with self.assertRaises(ValueError):
            register_dataset({"dataset_id": "x", "provider": "IMD", "quality_score": 5})

    def test_limit_validation_and_summary(self):
        register_dataset({"dataset_id": "a", "provider": "IMD", "variables": ["precipitation"]})
        with self.assertRaises(ValueError):
            search_datasets(limit=0)
        summary = catalog_summary()
        self.assertEqual(summary["dataset_count"], 1)
        self.assertEqual(summary["providers"], {"IMD": 1})

    def test_corrupt_catalog_degrades_gracefully(self):
        register_dataset({"dataset_id": "a", "provider": "IMD"})
        from backend.services.dataset_catalog_store import _catalog_file

        _catalog_file().write_text("{not json", encoding="utf-8")
        self.assertEqual(search_datasets(), [])
        self.assertEqual(load_catalog()["items"], [])


class ModelRegistryTests(unittest.TestCase):
    def test_registry_reports_inference_status_without_inventing_outputs(self):
        registry = get_model_registry()
        by_id = {model["model_id"]: model for model in registry["models"]}
        self.assertIn("imd-rainfall-moving-average", by_id)
        self.assertTrue(by_id["imd-rainfall-moving-average"]["outputs_produced"])
        # Prithvi-WxC must be gated: no compatible input means no output.
        if "prithvi-wxc-rollout" in by_id:
            prithvi = by_id["prithvi-wxc-rollout"]
            if prithvi["inference_status"] == "blocked":
                self.assertFalse(prithvi["outputs_produced"])
                self.assertTrue(prithvi["blockers"])

    def test_every_model_has_a_contract(self):
        for model in get_model_registry()["models"]:
            self.assertTrue(model["model_id"])
            self.assertTrue(model["version"])
            self.assertIn("input_contract", model)
            self.assertIn("output_contract", model)
            self.assertIn("outputs_produced", model)
            self.assertIn("inference_status", model)
            self.assertIn("validation", model)


class IntelligenceCapabilityTests(unittest.TestCase):
    def test_capabilities_declare_unavailable_layers(self):
        caps = get_intelligence_capabilities()
        self.assertTrue(caps["deterministic"])
        self.assertTrue(caps["llm_is_interpretation_layer_only"])
        layer_status = caps["layer_status"]
        self.assertEqual(layer_status["rainfall"], "connected")
        for layer in ("temperature", "lst", "sst"):
            self.assertEqual(layer_status[layer], "provider_required", layer)
        self.assertEqual(caps["no_data_message"], NO_DATA_MESSAGE)


class IntelligenceRoutingTests(unittest.TestCase):
    """A question naming a variable must be answered for that variable."""

    DATE = "2024-07-15"

    def test_unavailable_variable_returns_no_data_not_rainfall(self):
        os.environ.pop("CLIMATE_PROVIDER_TEMPERATURE_URL", None)
        result = answer_question("Why is temperature unavailable?", self.DATE, layer="rainfall")
        self.assertEqual(result["status"], "NO_DATA")
        self.assertTrue(result["provider_required"])

    def test_provenance_question_cites_the_dataset(self):
        result = answer_question("What data source produced this value?", self.DATE, layer="rainfall")
        self.assertEqual(result["layer"], "provenance")
        self.assertEqual(result["provenance"]["source"], "IMD")
        self.assertIn("RF25", result["provenance"]["dataset"])

    def test_model_question_reports_blocked_prithvi(self):
        result = answer_question("Is Prithvi-WxC currently available?", self.DATE)
        self.assertEqual(result["layer"], "models")
        self.assertEqual(result["prithvi_status"], "blocked")

    def test_risk_question_uses_risk_engine(self):
        result = answer_question("Which regions have high climate risk?", self.DATE, layer="rainfall")
        self.assertEqual(result["layer"], "risk")
        self.assertEqual(result["source"], "rainfall hazard engine")

    def test_unsupported_layer_is_rejected(self):
        with self.assertRaises(ValueError):
            answer_question("anything", self.DATE, layer="not_a_layer")

    def test_empty_question_is_rejected(self):
        with self.assertRaises(ValueError):
            answer_question("   ", self.DATE)


class RouteModuleIntegrityTests(unittest.TestCase):
    """Guard route modules against undefined names and dead imports.

    A route that calls a helper without importing it only fails at request
    time, so a static check here catches that class of defect in CI.
    """

    def _undefined_names(self, path: str) -> set[str]:
        import ast
        import builtins

        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
        defined: set[str] = set(dir(builtins))
        defined |= {"__file__", "__name__", "__doc__", "__package__", "__builtins__"}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defined.add(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                defined.add(node.id)
            elif isinstance(node, ast.arg):
                defined.add(node.arg)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    defined.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    defined.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(node, ast.ExceptHandler) and node.name:
                defined.add(node.name)
            elif isinstance(node, ast.comprehension) and isinstance(node.target, ast.Name):
                defined.add(node.target.id)

        used = {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
        }
        return used - defined

    def test_route_modules_have_no_undefined_globals(self):
        for path in (
            "backend/api/main.py",
            "backend/api/platform_routes.py",
            "backend/api/ogc_routes.py",
        ):
            with self.subTest(module=path):
                self.assertEqual(self._undefined_names(path), set())


class ErrorMappingContractTests(unittest.TestCase):
    """Verify service failures map to correct HTTP semantics.

    A missing dependency (no PostGIS, no dataset) must be 503, not an opaque
    500, and internal detail must not be echoed to clients.
    """

    def test_runtime_error_handler_returns_503_without_leaking_detail(self):
        import asyncio

        from backend.api.main import _service_unavailable

        response = asyncio.run(
            _service_unavailable(None, RuntimeError("DATABASE_URL is not configured at /secret/path"))
        )
        self.assertEqual(response.status_code, 503)
        body = response.body.decode()
        self.assertNotIn("DATABASE_URL", body)
        self.assertNotIn("/secret/path", body)

    def test_file_not_found_handler_returns_503_without_path(self):
        import asyncio

        from backend.api.main import _dataset_unavailable

        response = asyncio.run(
            _dataset_unavailable(None, FileNotFoundError("/abs/path/to/RF25.nc"))
        )
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("RF25.nc", response.body.decode())

    def test_handlers_are_registered_on_the_app(self):
        from backend.api.main import app

        handlers = app.exception_handlers
        self.assertIn(RuntimeError, handlers)
        self.assertIn(FileNotFoundError, handlers)


class OperatorBoundaryTests(unittest.TestCase):
    def test_status_reports_disabled_development_mode(self):
        old = os.environ.pop("ADMIN_API_KEY", None)
        try:
            status = operator_auth_status()
            self.assertFalse(status["admin_api_key_configured"])
            self.assertEqual(status["operator_boundary"], "disabled_development_mode")

            class _Request:
                headers = {}

            require_operator(_Request())  # no exception in development mode
        finally:
            if old is not None:
                os.environ["ADMIN_API_KEY"] = old


if __name__ == "__main__":
    unittest.main()