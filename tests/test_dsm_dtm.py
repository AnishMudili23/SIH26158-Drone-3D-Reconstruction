"""Regression test for src/exports/dsm_dtm.py — catches a real bug found while
building this: np.maximum.at on a NaN-initialized accumulator propagates NaN forever
(max(nan, x) is nan under IEEE semantics), so the DSM grid came back entirely NaN."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from exports.dsm_dtm import grid_elevation


def test_max_aggregation_does_not_stay_all_nan():
    points_enu = np.array([[0.0, 0.0, 1.0], [1.0, 1.0, 5.0], [9.0, 9.0, 3.0]])
    grid, x_min, y_max = grid_elevation(points_enu, None, cell_size_m=5.0, agg="max")
    assert not np.isnan(grid).all()
    assert np.nanmax(grid) == 5.0


def test_min_aggregation_correct():
    points_enu = np.array([[0.0, 0.0, 1.0], [0.5, 0.5, 5.0], [9.0, 9.0, 3.0]])
    grid, x_min, y_max = grid_elevation(points_enu, None, cell_size_m=5.0, agg="min")
    assert np.nanmin(grid) == 1.0


def test_empty_cells_are_nan_not_zero():
    # Sparse points in a large grid should leave most cells genuinely empty (NaN),
    # never silently defaulting to 0 (which would misrepresent "unknown" as "ground level").
    points_enu = np.array([[0.0, 0.0, 10.0]])
    grid, _, _ = grid_elevation(points_enu, None, cell_size_m=1.0, agg="max")
    assert grid.size == 1  # single point -> single cell, no room for empty cells here

    points_enu2 = np.array([[0.0, 0.0, 10.0], [50.0, 50.0, 20.0]])
    grid2, _, _ = grid_elevation(points_enu2, None, cell_size_m=1.0, agg="max")
    assert np.isnan(grid2).any()
    assert not np.any(grid2 == 0)
