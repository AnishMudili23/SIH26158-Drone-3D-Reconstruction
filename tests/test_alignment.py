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
    from geo.scale_alignment import _rederive_pose_for_aligned_world, rederive_aligned_camera
    from common.coordinate_frames import SimilarityTransform, project_world_point

    rng = np.random.default_rng(0)
    # Generate proper orthonormal rotation matrices (det == +1)
    q1, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    if np.linalg.det(q1) < 0:
        q1[:, 0] *= -1
    r_orig = q1
    t_orig = rng.normal(size=3)
    k = np.array([[800.0, 0.0, 320.0], [0.0, 800.0, 240.0], [0.0, 0.0, 1.0]])
    pose = CameraPose(frame_path="f.jpg", rotation=r_orig, translation=t_orig, intrinsics=k)

    scale = 3.7
    q2, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    if np.linalg.det(q2) < 0:
        q2[:, 0] *= -1
    rot = q2
    t = rng.normal(size=3)
    transform = SimilarityTransform(scale=scale, rotation=rot, translation=t)

    # Point in front of camera
    c_orig = -r_orig.T @ t_orig
    x_orig = c_orig + r_orig.T @ np.array([1.0, 2.0, 15.0])
    x_aligned = transform.transform_points(x_orig)

    new_pose = _rederive_pose_for_aligned_world(pose, scale, rot, t)
    aligned_pose, traj_enu = rederive_aligned_camera(pose, transform)

    # 1. Rotation is strictly orthonormal (det == 1 and R @ R.T == I)
    np.testing.assert_allclose(new_pose.rotation @ new_pose.rotation.T, np.eye(3), atol=1e-9)
    assert np.linalg.det(new_pose.rotation) == pytest.approx(1.0, rel=1e-6)

    # 2. Camera center is exactly transformed into ENU: C_enu = -R.T @ t
    c_aligned_expected = transform.transform_camera_center(c_orig)
    np.testing.assert_allclose(-new_pose.rotation.T @ new_pose.translation, c_aligned_expected, atol=1e-9)
    np.testing.assert_allclose(traj_enu.center_enu, c_aligned_expected, atol=1e-9)

    # 3. Pinhole projection of aligned 3D point matches original SfM projection exactly
    p_cam_direct = r_orig @ x_orig + t_orig
    p_pix_direct = k @ (p_cam_direct / p_cam_direct[2])

    p_cam_aligned = new_pose.rotation @ x_aligned + new_pose.translation
    p_pix_aligned = k @ (p_cam_aligned / p_cam_aligned[2])
    np.testing.assert_allclose(p_pix_direct[:2], p_pix_aligned[:2], atol=1e-9)

    # 4. project_world_point produces identical pixel coordinates
    p_proj = project_world_point(x_aligned, traj_enu.center_enu, traj_enu.rotation, k)
    np.testing.assert_allclose(p_pix_direct[:2], p_proj, atol=1e-9)


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
