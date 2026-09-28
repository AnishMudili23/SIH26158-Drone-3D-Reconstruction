import numpy as np
import pytest

from common.coordinate_frames import (
    CoordinateFrame,
    SimilarityTransform,
    CameraTrajectoryENU,
    wgs84_to_enu,
    enu_to_wgs84,
    wgs84_to_utm,
    enu_to_utm,
    sfm_to_enu,
    enu_to_sfm,
    project_world_point,
)
from common.geometry_interface import CameraPose, GeometryEstimate


def test_similarity_transform_points_and_inverse():
    scale = 2.45
    # Rotation 90 degrees around Z
    rot = np.array([
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ])
    trans = np.array([10.0, -5.0, 30.0])
    st = SimilarityTransform(scale=scale, rotation=rot, translation=trans)

    pts = np.array([
        [1.0, 2.0, 3.0],
        [0.0, 0.0, 0.0],
        [-4.0, 5.0, 10.0],
    ])

    dst = st.transform_points(pts)
    # Check point 0: scale * [-2, 1, 3] + [10, -5, 30] = [-4.9 + 10, 2.45 - 5, 7.35 + 30]
    expected_p0 = 2.45 * np.array([-2.0, 1.0, 3.0]) + trans
    np.testing.assert_allclose(dst[0], expected_p0, atol=1e-7)

    # Inverse transform
    inv_st = st.inverse()
    recovered = inv_st.transform_points(dst)
    np.testing.assert_allclose(recovered, pts, atol=1e-7)


def test_similarity_transform_vectors():
    rot = np.array([
        [0.0, -1.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0],
    ])
    st = SimilarityTransform(scale=5.0, rotation=rot, translation=np.array([100.0, 200.0, 300.0]))
    normal = np.array([1.0, 0.0, 0.0])
    rot_normal = st.transform_vectors(normal)
    # Vector should rotate by rot, unaffected by scale or translation
    np.testing.assert_allclose(rot_normal, np.array([0.0, 1.0, 0.0]), atol=1e-7)


def test_coordinate_frames_round_trip():
    lat0, lon0, alt0 = 47.38435, 8.54518, 475.0
    lats = np.array([47.38450, 47.38480, 47.38420])
    lons = np.array([8.54530, 8.54560, 8.54500])
    alts = np.array([480.0, 490.0, 470.0])

    enu = wgs84_to_enu(lats, lons, alts, lat0, lon0, alt0)
    assert enu.shape == (3, 3)

    back_wgs = enu_to_wgs84(enu, lat0, lon0, alt0)
    np.testing.assert_allclose(back_wgs[:, 0], lats, atol=1e-6)
    np.testing.assert_allclose(back_wgs[:, 1], lons, atol=1e-6)
    np.testing.assert_allclose(back_wgs[:, 2], alts, atol=1e-4)


def test_camera_trajectory_enu_contract():
    c_enu = np.array([15.0, 25.0, 50.0])
    rot = np.eye(3)
    k = np.array([[600.0, 0.0, 300.0], [0.0, 600.0, 200.0], [0.0, 0.0, 1.0]])

    traj = CameraTrajectoryENU(
        frame_path="frame_001.jpg",
        center_enu=c_enu,
        rotation=rot,
        intrinsics=k,
        coordinate_frame=CoordinateFrame.ENU,
    )

    # Translation property
    np.testing.assert_allclose(traj.translation, -c_enu, atol=1e-7)

    # Conversion to CameraPose
    pose = traj.to_camera_pose()
    assert pose.coordinate_frame == CoordinateFrame.ENU
    np.testing.assert_allclose(pose.camera_center, c_enu, atol=1e-7)

    # Projection
    pt_world = np.array([15.0, 25.0, 60.0])  # 10m directly along optical axis (Z)
    pixel = traj.project_point(pt_world)
    np.testing.assert_allclose(pixel, [300.0, 200.0], atol=1e-5)
