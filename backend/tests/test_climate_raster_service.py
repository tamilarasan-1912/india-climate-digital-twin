import unittest
import xarray as xr
import numpy as np

from backend.services.climate_raster_service import raster_contract, spatial_subset, tile_xyz_bounds, validate_regular_grid


class ClimateRasterTests(unittest.TestCase):
    def test_tile_bounds(self):
        bbox = tile_xyz_bounds(0, 0, 0)
        self.assertAlmostEqual(bbox[0], -180.0)
        self.assertAlmostEqual(bbox[2], 180.0)

    def test_grid_validation_and_subset(self):
        ds = xr.Dataset(
            {"rain": (("LATITUDE", "LONGITUDE"), np.arange(9).reshape(3, 3))},
            coords={"LATITUDE": [10.0, 11.0, 12.0], "LONGITUDE": [70.0, 71.0, 72.0]},
        )
        meta = validate_regular_grid(ds, "rain")
        self.assertEqual(meta["dimensions"]["LATITUDE"], 3)
        subset = spatial_subset(ds, "rain", (70.5, 10.5, 72.0, 12.0))
        self.assertGreater(subset.size, 0)

    def test_contract_is_explicit(self):
        result = raster_contract(layer="rainfall", provider="IMD", variable="precipitation", units="mm", source_path=None, date="2024-07-15")
        self.assertEqual(result["contract"], "india-climate-raster/v1")
        self.assertIn("endpoint_template", result["tiling"])
        self.assertIsNone(result["source"])

if __name__ == "__main__":
    unittest.main()
