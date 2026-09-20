import numpy as np

from backend.services.spatial_aggregation_service import aggregate_grid_to_feature


def test_polygon_grid_aggregation():
    feature = {
        "type": "Feature",
        "properties": {"id": "test"},
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]}
    }
    result = aggregate_grid_to_feature(
        np.array([[1.0, 2.0], [3.0, 4.0]]),
        np.array([0.5, 1.5]),
        np.array([0.5, 1.5]),
        feature,
    )
    assert result["status"] == "available"
    assert result["valid_grid_cells"] == 4
    assert result["mean"] == 2.5
