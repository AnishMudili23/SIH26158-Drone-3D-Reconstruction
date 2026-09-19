"""Regression test for src/pointcloud/outlier_removal.py — catches a real
over-aggressive-radius-filtering bug found while testing against a real COLMAP
reconstruction (radius filtering with a naive auto-radius rejected 98.9% of points on
a real, highly non-uniform-density point cloud)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pointcloud.outlier_removal import clean_point_cloud, remove_statistical_outliers


def test_statistical_removal_drops_only_true_outliers():
    rng = np.random.default_rng(0)
    cluster = rng.normal(0, 1.0, (200, 3))
    wild_outliers = np.array([[500.0, 500.0, 500.0], [-400.0, 0.0, 0.0]])
    points = np.vstack([cluster, wild_outliers])

    mask, _ = remove_statistical_outliers(points, nb_neighbors=20, std_ratio=2.0)
    assert mask[:200].sum() >= 195  # keeps almost all the real cluster
    assert not mask[200:].any()     # drops both wild outliers


def test_clean_point_cloud_default_does_not_over_filter_sparse_regions():
    # Two well-separated but each internally-sane clusters (simulates real SfM point
    # density variation: dense near well-observed surfaces, sparser elsewhere) plus a
    # couple of genuine wild outliers.
    rng = np.random.default_rng(1)
    dense_cluster = rng.normal(0, 0.3, (150, 3))
    sparse_cluster = rng.normal([20, 20, 20], 2.0, (30, 3))
    wild_outliers = np.array([[1000.0, 0.0, 0.0], [0.0, -900.0, 0.0]])
    points = np.vstack([dense_cluster, sparse_cluster, wild_outliers])

    mask = clean_point_cloud(points)  # radius filter off by default
    kept = points[mask]

    assert not mask[-2:].any(), "wild outliers must still be removed"
    assert mask.sum() > 0.9 * (points.shape[0] - 2), "should not aggressively over-filter valid sparse points"
    assert kept[:, 0].max() < 100  # extent no longer dominated by the wild outliers
