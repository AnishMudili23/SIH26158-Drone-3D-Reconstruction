"""Regression tests for src/confidence/confidence_report.py (Phase 6)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from confidence.confidence_report import build_confidence_report, compute_confidence_tiers


def test_high_confidence_requires_both_signals():
    track_len = np.array([10, 10, 1, 1])
    reproj_error = np.array([0.1, 5.0, 0.1, 5.0])
    tiers = compute_confidence_tiers(track_len, reproj_error)
    # Only (high track_len, low error) should be "high" (tier 2).
    assert tiers[0] == 2
    assert tiers[1] != 2  # good track length but bad reprojection error
    assert tiers[2] != 2  # good error but bad track length
    assert tiers[3] == 0


def test_region_grid_leaves_unobserved_cells_as_nan():
    # Two tightly clustered points far away from a third isolated point creates an
    # empty cell in between them (bin size chosen deliberately to open a gap).
    points_xyz = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 0.0], [100.0, 100.0, 0.0]])
    track_len = np.array([5, 5, 5])
    reproj_error = np.array([0.5, 0.5, 0.5])
    class_names = ["Building", "Building", "Road"]

    report = build_confidence_report(points_xyz, track_len, reproj_error, class_names, region_cell_size_m=5.0)
    assert report.pct_grid_cells_unobserved > 0
    assert np.isnan(report.region_grid.mean_tier_grid).any()


def test_per_class_breakdown_sums_to_total_points():
    rng = np.random.default_rng(5)
    n = 500
    points_xyz = rng.uniform(0, 20, (n, 3))
    track_len = rng.integers(1, 8, n).astype(float)
    reproj_error = rng.uniform(0.1, 3.0, n)
    class_names = rng.choice(["Building", "Road", "Tree"], n).tolist()

    report = build_confidence_report(points_xyz, track_len, reproj_error, class_names)
    assert sum(c.n_points for c in report.per_class) == n
