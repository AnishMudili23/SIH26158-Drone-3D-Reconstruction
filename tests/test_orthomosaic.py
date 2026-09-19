"""Regression tests for src/exports/orthomosaic.py (Phase 7)."""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from common.geometry_interface import CameraPose
from exports.orthomosaic import build_orthomosaic, ground_plane_homography


def test_nadir_homography_maps_directly_below_camera_to_principal_point():
    r = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=float)
    k = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=float)
    c = np.array([0, 0, 50.0])
    t = -r @ c
    pose = CameraPose(frame_path="f.jpg", rotation=r, translation=t, intrinsics=k)

    h = ground_plane_homography(pose, z_ref=0.0)
    p = h @ np.array([0, 0, 1.0])
    p = p[:2] / p[2]
    np.testing.assert_allclose(p, [320, 240], atol=1e-9)

    # 1m east at ground level should shift by focal_length / altitude pixels.
    p2 = h @ np.array([1, 0, 1.0])
    p2 = p2[:2] / p2[2]
    assert p2[0] - p[0] == pytest.approx(500 / 50)


def test_build_orthomosaic_places_marker_at_correct_world_position(tmp_path):
    image_dir = tmp_path
    img = np.full((480, 640, 3), 50, dtype=np.uint8)
    cv2.rectangle(img, (300, 220), (340, 260), (0, 0, 255), -1)  # red marker near center
    cv2.imwrite(str(image_dir / "frame_000.jpg"), img)

    r = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=float)
    k = np.array([[500, 0, 320], [0, 500, 240], [0, 0, 1]], dtype=float)
    c = np.array([0, 0, 50.0])
    t = -r @ c
    pose = CameraPose(frame_path="frame_000.jpg", rotation=r, translation=t, intrinsics=k)

    ortho, count = build_orthomosaic(
        [pose], image_dir, x_min=-20, x_max=20, y_min=-20, y_max=20, z_ref=0.0, gsd_m=0.1
    )
    assert (count > 0).mean() == 1.0
    center = ortho[ortho.shape[0] // 2, ortho.shape[1] // 2]
    assert center[2] > 200 and center[0] < 50  # red channel high, blue channel low (BGR)
