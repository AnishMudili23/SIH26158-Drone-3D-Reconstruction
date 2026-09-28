import numpy as np
import pytest

from depth_fusion.dense_fusion_pipeline import (
    DenseDepthFusionPipeline,
    DepthSource,
    DensePointBatch,
)
from depth_fusion.multiview_consistency import ViewCamera


def test_fit_metric_depth_synthetic():
    pipeline = DenseDepthFusionPipeline()
    h, w = 100, 100
    a_true, b_true = 2.5, -0.8
    rel_depth = np.random.uniform(2.0, 10.0, (h, w)).astype(np.float32)
    metric_true = a_true * rel_depth + b_true

    R = np.eye(3)
    t = np.zeros(3)
    K = np.array([[100, 0, 50], [0, 100, 50], [0, 0, 1]], dtype=float)

    points2d = []
    point3d_id_to_xyz = {}
    for i in range(25):
        u, v = np.random.uniform(10, 90, 2)
        z = float(metric_true[int(round(v)), int(round(u))])
        xyz = np.linalg.inv(K) @ np.array([u, v, 1.0]) * z
        points2d.append((u, v, i))
        point3d_id_to_xyz[i] = xyz

    depth_map, a, b, res = pipeline.fit_metric_depth(
        rel_depth, R, t, points2d, point3d_id_to_xyz
    )
    assert depth_map is not None
    assert a == pytest.approx(a_true, rel=1e-3)
    assert b == pytest.approx(b_true, abs=1e-3)
    assert res < 1e-4


def test_depth_sources_classified():
    batch = DensePointBatch(
        points_xyz=np.zeros((10, 3)),
        points_rgb=np.zeros((10, 3), dtype=np.uint8),
        confidences=np.array([0.95, 0.85, 0.50, 0.40, 0.90, 0.70, 0.60, 0.88, 0.30, 0.92]),
        sources=[DepthSource.MVS_AI.value] * 5 + [DepthSource.AI.value] * 5,
        n_consistent=10,
        n_rejected=2,
    )
    assert len(batch.sources) == 10
    assert DepthSource.MVS_AI.value in batch.sources
    assert DepthSource.AI.value in batch.sources
