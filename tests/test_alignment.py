"""Regression tests for src/common/alignment.py and src/geo/scale_alignment.py —
consolidates the ad-hoc synthetic validation done while building Phase 3."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from common.alignment import umeyama_alignment
from common.geometry_interface import CameraPose, GeometryEstimate
from geo.scale_alignment import (
    GpsFix,
    _ECEF_FROM_GPS,
    _GPS_FROM_ECEF,
    _enu_rotation_matrix,
    align_geometry_to_gps,
    enu_to_gps,
    gps_fixes_to_enu,
)


def test_umeyama_recovers_known_scale_rotation_translation():
    rng = np.random.default_rng(0)
    src = rng.uniform(-10, 10, (30, 3))
    true_scale, true_r, true_t = 2.3, np.eye(3), np.array([5.0, -3.0, 1.0])
    dst = true_scale * (true_r @ src.T).T + true_t

    scale, r, t = umeyama_alignment(src, dst)
    assert scale == pytest.approx(true_scale, rel=1e-9)
    np.testing.assert_allclose(r, true_r, atol=1e-9)
    np.testing.assert_allclose(t, true_t, atol=1e-7)


def test_enu_round_trip_is_accurate():
    fixes = [
        GpsFix("a", 12.9716, 77.5946, 900.0),
        GpsFix("b", 12.9720, 77.5950, 905.0),
        GpsFix("c", 12.9725, 77.5955, 910.0),
    ]
    enu, lat0, lon0, alt0 = gps_fixes_to_enu(fixes)
    back = enu_to_gps(enu, lat0, lon0, alt0)
    original = np.array([[f.lat, f.lon, f.alt_m] for f in fixes])
    np.testing.assert_allclose(back, original, atol=1e-6)


def test_align_geometry_to_gps_recovers_known_scale():
    rng = np.random.default_rng(1)
    n = 20
    true_centers = np.stack([np.linspace(0, 100, n), np.zeros(n), np.full(n, 50.0)], axis=1)
    true_scale = 2.5
    sfm_centers = true_scale * true_centers

    poses = []
    for i in range(n):
        r = np.eye(3)
        c = sfm_centers[i]
        t = -r @ c
        poses.append(CameraPose(frame_path=f"frame_{i:03d}.jpg", rotation=r, translation=t, intrinsics=np.eye(3)))

    points_xyz = true_scale * rng.uniform(-50, 150, (200, 3))
    geometry = GeometryEstimate(
        poses=poses, points_xyz=points_xyz, points_rgb=None, points_confidence=None,
        backend_name="colmap", is_metric_scale=False,
    )

    lat0, lon0, alt0 = 12.9716, 77.5946, 900.0
    origin_ecef = np.array(_ECEF_FROM_GPS.transform(lon0, lat0, alt0))
    r_enu = _enu_rotation_matrix(lat0, lon0)
    fixes = []
    for i in range(n):
        ecef = r_enu.T @ true_centers[i] + origin_ecef
        lon, lat, alt = _GPS_FROM_ECEF.transform(ecef[0], ecef[1], ecef[2])
        fixes.append(GpsFix(f"frame_{i:03d}.jpg", lat, lon, alt))

    result = align_geometry_to_gps(geometry, fixes)
    assert result.scale_factor == pytest.approx(1.0 / true_scale, rel=1e-6)
    assert result.mean_alignment_residual_m < 1e-6
    assert result.n_gps_correspondences == n


def test_rederive_pose_for_aligned_world_projects_identically():
    from geo.scale_alignment import _rederive_pose_for_aligned_world

    rng = np.random.default_rng(0)
    r_orig = np.linalg.qr(rng.normal(size=(3, 3)))[0]
    t_orig = rng.normal(size=3)
    pose = CameraPose(frame_path="f.jpg", rotation=r_orig, translation=t_orig, intrinsics=np.eye(3))

    scale = 3.7
    rot = np.linalg.qr(rng.normal(size=(3, 3)))[0]
    t = rng.normal(size=3)

    x_orig = rng.normal(size=3)
    x_aligned = scale * rot @ x_orig + t

    x_cam_direct = r_orig @ x_orig + t_orig
    new_pose = _rederive_pose_for_aligned_world(pose, scale, rot, t)
    x_cam_via_aligned = new_pose.rotation @ x_aligned + new_pose.translation

    np.testing.assert_allclose(x_cam_direct, x_cam_via_aligned, atol=1e-9)


def test_align_geometry_to_gps_raises_on_too_few_matches():
    poses = [
        CameraPose(frame_path="only_one.jpg", rotation=np.eye(3), translation=np.zeros(3), intrinsics=np.eye(3))
    ]
    geometry = GeometryEstimate(
        poses=poses, points_xyz=np.zeros((1, 3)), points_rgb=None, points_confidence=None,
        backend_name="colmap", is_metric_scale=False,
    )
    fixes = [GpsFix("only_one.jpg", 0.0, 0.0, 0.0)]
    with pytest.raises(ValueError):
        align_geometry_to_gps(geometry, fixes)
