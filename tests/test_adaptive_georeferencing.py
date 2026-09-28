import numpy as np
import pytest

from common.geometry_interface import CameraPose, GeometryEstimate
from geo.scale_alignment import GpsFix
from geo.adaptive_georeferencing import (
    GeoreferencingMode,
    AdaptiveGeoreferencer,
    ransac_similarity_alignment,
)
from common.coordinate_frames import CoordinateFrame, SimilarityTransform
from sensor_fusion.sensor_quality import GPSQualityTier, SensorQualityEvaluator


def test_ransac_similarity_rejects_gps_outlier():
    rng = np.random.default_rng(42)
    n = 25
    src = rng.uniform(-50, 50, (n, 3))
    true_scale = 1.8
    # 3D rotation
    q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    if np.linalg.det(q) < 0:
        q[:, 0] *= -1
    true_r = q
    true_t = np.array([20.0, -15.0, 5.0])

    dst = true_scale * (true_r @ src.T).T + true_t

    # Inject 3 severe GPS jump outliers (e.g. multipath or 50m jump)
    dst[3] += np.array([50.0, -40.0, 30.0])
    dst[11] += np.array([-70.0, 60.0, -20.0])
    dst[19] += np.array([45.0, 55.0, -35.0])

    tf, inliers, residual = ransac_similarity_alignment(src, dst, inlier_threshold_m=4.0)

    # Outliers must be rejected
    assert not inliers[3]
    assert not inliers[11]
    assert not inliers[19]
    assert inliers.sum() >= 20

    # Recovered scale, rotation, translation should match ground truth closely
    assert tf.scale == pytest.approx(true_scale, rel=1e-2)
    np.testing.assert_allclose(tf.rotation, true_r, atol=2e-2)
    np.testing.assert_allclose(tf.translation, true_t, atol=0.5)


def test_adaptive_georeferencer_strong_gps():
    rng = np.random.default_rng(10)
    n = 20
    # Long corridor flight: baseline 150m
    t = np.linspace(0, 150, n)
    true_centers = np.column_stack([t, 0.5 * t, np.full(n, 30.0)])
    true_scale = 2.0
    sfm_centers = true_scale * true_centers

    poses = []
    for i in range(n):
        r = np.eye(3)
        c = sfm_centers[i]
        poses.append(CameraPose(
            frame_path=f"f_{i:03d}.jpg",
            rotation=r,
            translation=-r @ c,
            intrinsics=np.eye(3),
        ))

    points = rng.uniform(-10, 100, (100, 3)) * true_scale
    geom = GeometryEstimate(
        poses=poses,
        points_xyz=points,
        points_rgb=None,
        points_confidence=None,
        backend_name="colmap",
        is_metric_scale=False,
    )

    # GPS fixes in ENU with 1m noise
    gps_fixes = []
    lat0, lon0, alt0 = 47.38, 8.54, 450.0
    for i in range(n):
        c = true_centers[i]
        # Fake lat/lon roughly
        d_lat = c[1] / 111320.0
        d_lon = c[0] / (111320.0 * np.cos(np.radians(lat0)))
        gps_fixes.append(GpsFix(
            frame_name=f"f_{i:03d}.jpg",
            lat=lat0 + d_lat,
            lon=lon0 + d_lon,
            alt_m=alt0 + c[2],
        ))

    georeferencer = AdaptiveGeoreferencer()
    res = georeferencer.estimate(geom, gps_fixes)

    assert res.coordinate_frame == CoordinateFrame.ENU
    assert res.scale_factor == pytest.approx(1.0 / true_scale, rel=1e-2)
    assert len(res.aligned_poses) == n
    assert res.camera_trajectory is not None
    assert len(res.camera_trajectory) == n

    # Poses are strictly orthonormal
    for p in res.aligned_poses:
        np.testing.assert_allclose(p.rotation @ p.rotation.T, np.eye(3), atol=1e-7)


def test_adaptive_georeferencer_insufficient_baseline_reverts_to_local_metric():
    # Synthetic hover: drone stays within 1m box, noise 6m -> BNR < 0.5
    rng = np.random.default_rng(20)
    n = 10
    hover_centers = rng.uniform(-0.5, 0.5, (n, 3))

    poses = [
        CameraPose(
            frame_path=f"f_{i:03d}.jpg",
            rotation=np.eye(3),
            translation=-hover_centers[i],
            intrinsics=np.eye(3),
        )
        for i in range(n)
    ]
    geom = GeometryEstimate(
        poses=poses,
        points_xyz=rng.uniform(-5, 5, (50, 3)),
        points_rgb=None,
        points_confidence=None,
        backend_name="colmap",
        is_metric_scale=False,
    )

    hover_enu = rng.uniform(-0.5, 0.5, (n, 3))
    lat0, lon0, alt0 = 47.38, 8.54, 450.0
    from common.coordinate_frames import enu_to_wgs84
    wgs = enu_to_wgs84(hover_enu, lat0, lon0, alt0)

    gps_fixes = [
        GpsFix(
            frame_name=f"f_{i:03d}.jpg",
            lat=float(wgs[i, 0]),
            lon=float(wgs[i, 1]),
            alt_m=float(wgs[i, 2]),
        )
        for i in range(n)
    ]

    georeferencer = AdaptiveGeoreferencer(default_gps_noise_m=6.0)
    res = georeferencer.estimate(geom, gps_fixes)

    # Must revert to LOCAL_METRIC to avoid diverging on noise
    assert res.coordinate_frame == CoordinateFrame.LOCAL_METRIC
    assert res.scale_factor == 1.0  # Visual scale locked
