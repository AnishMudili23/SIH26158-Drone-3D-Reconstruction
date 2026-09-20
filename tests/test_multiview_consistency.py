import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depth_fusion.multiview_consistency import (
    MultiViewDepthConsistencyFilter,
    ViewCamera,
)


def _make_camera(tx: float, ty: float, tz: float, w: int = 100, h: int = 100) -> ViewCamera:
    K = np.array([
        [100.0, 0.0, 50.0],
        [0.0, 100.0, 50.0],
        [0.0, 0.0, 1.0],
    ], dtype=np.float64)
    # Looking down +Z axis
    R = np.eye(3, dtype=np.float64)
    t = np.array([tx, ty, tz], dtype=np.float64)
    return ViewCamera(rotation=R, translation=t, intrinsics=K, width=w, height=h)


def test_consistent_synthetic_views_pass():
    # Camera A at origin (0, 0, 0), Camera B translated by 0.5m along X
    cam_a = _make_camera(0.0, 0.0, 0.0)
    cam_b = _make_camera(-0.5, 0.0, 0.0)

    # Flat plane at world Z = 10.0m
    depth_a = np.full((100, 100), 10.0, dtype=np.float32)
    depth_b = np.full((100, 100), 10.0, dtype=np.float32)

    filter_engine = MultiViewDepthConsistencyFilter(max_relative_depth_error=0.05)
    consistent_mask, rel_err = filter_engine.check_consistency_pair(depth_a, cam_a, depth_b, cam_b)

    # Center region of camera A should reproject cleanly into camera B with near-zero error
    center_consistent = consistent_mask[30:70, 30:70]
    assert np.all(center_consistent)
    assert np.mean(rel_err[30:70, 30:70]) < 0.01


def test_conflicting_ai_hallucination_rejected():
    cam_a = _make_camera(0.0, 0.0, 0.0)
    cam_b = _make_camera(-0.5, 0.0, 0.0)

    # Camera A has a hallucinated 5.0m depth patch in the center
    depth_a = np.full((100, 100), 10.0, dtype=np.float32)
    depth_a[40:60, 40:60] = 5.0  # 50% depth hallucination error

    # Camera B has the true 10.0m flat surface
    depth_b = np.full((100, 100), 10.0, dtype=np.float32)

    filter_engine = MultiViewDepthConsistencyFilter(max_relative_depth_error=0.05)
    consistent_mask, rel_err = filter_engine.check_consistency_pair(depth_a, cam_a, depth_b, cam_b)

    # Hallucinated region must be rejected
    assert not np.any(consistent_mask[45:55, 45:55])
    assert np.all(rel_err[45:55, 45:55] > 0.30)


def test_confidence_weighted_fusion_prioritization():
    # True surface depth 10.0
    # MVS has high confidence on left half, missing on right half
    mvs_depth = np.full((50, 50), 10.0, dtype=np.float32)
    mvs_conf = np.zeros((50, 50), dtype=np.float32)
    mvs_conf[:, :25] = 0.95  # left half strong MVS

    # AI depth has good prediction 10.1 across the whole image with high consistency
    ai_depth = np.full((50, 50), 10.1, dtype=np.float32)
    ai_weight = np.full((50, 50), 0.90, dtype=np.float32)

    fused = MultiViewDepthConsistencyFilter.fuse_mvs_and_ai_depth(
        mvs_depth, mvs_conf, ai_depth, ai_weight
    )

    # Left half should be dominated by MVS (~10.0)
    assert np.isclose(np.mean(fused[:, :25]), 10.0, atol=0.02)
    # Right half should be filled by AI depth (~10.1)
    assert np.isclose(np.mean(fused[:, 25:]), 10.1, atol=0.02)
