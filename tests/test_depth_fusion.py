"""Regression test for src/depth_fusion/fuse_depth.py's scale/shift fit + backprojection
(Phase 5) — catches the pixel-rounding consistency bug found while building this."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from depth_fusion.fuse_depth import fuse_frame


def test_fuse_frame_recovers_known_affine_scale_shift():
    rng = np.random.default_rng(2)
    h, w = 200, 300
    k = np.array([[150, 0, 150], [0, 150, 100], [0, 0, 1]], dtype=float)
    r = np.eye(3)
    t = np.zeros(3)

    a_true, b_true = 3.7, -1.2
    image_bgr = np.zeros((h, w, 3), dtype=np.uint8)

    points2d = []
    point3d_id_to_xyz = {}
    relative_depth = np.zeros((h, w))
    for i in range(80):
        u = rng.uniform(20, w - 20)
        v = rng.uniform(20, h - 20)
        z = rng.uniform(5, 20)
        x_cam = np.linalg.inv(k) @ np.array([u, v, 1.0]) * z
        point3d_id_to_xyz[i] = x_cam
        points2d.append((u, v, i))
        # NOTE: must round consistently with fuse_frame's own pixel lookup
        # (int(round(...))) — using plain int() here previously produced a
        # nonsensical fit purely from test-side pixel misalignment, not a real bug.
        relative_depth[int(round(v)), int(round(u))] = (z - b_true) / a_true

    result = fuse_frame(
        image_bgr, relative_depth, r, t, k, points2d, point3d_id_to_xyz,
        max_dense_points=5000, min_correspondences=8,
    )
    assert result is not None
    _, _, fit = result
    assert fit.scale_a == pytest.approx(a_true, rel=1e-6)
    assert fit.shift_b == pytest.approx(b_true, abs=1e-6)
    assert fit.fit_residual < 1e-6


def test_fuse_frame_returns_none_below_min_correspondences():
    h, w = 50, 50
    k = np.eye(3)
    result = fuse_frame(
        np.zeros((h, w, 3), dtype=np.uint8), np.zeros((h, w)), np.eye(3), np.zeros(3), k,
        points2d=[(10, 10, 0), (20, 20, 1)],
        point3d_id_to_xyz={0: np.array([0, 0, 1.0]), 1: np.array([0, 0, 2.0])},
        min_correspondences=8,
    )
    assert result is None
