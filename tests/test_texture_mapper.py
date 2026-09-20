import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from exports.texture_mapper import CameraView, UVTextureMapper


def test_triangle_camera_view_assignment(tmp_path):
    # Triangle facing up towards +Z (flat plane on XY at Z=0)
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
    ], dtype=np.float64)
    faces = np.array([[0, 1, 2]], dtype=np.int32)

    # Synthetic texture image
    img_path = tmp_path / "cam0.png"
    Image.new("RGB", (200, 200), color=(100, 150, 200)).save(img_path)

    # Camera directly overhead looking down at the triangle
    K = np.array([[100.0, 0.0, 100.0], [0.0, 100.0, 100.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    # Camera at [0.5, 0.5, 5.0] looking down
    R = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], dtype=np.float64)
    t = -R @ np.array([0.3, 0.3, 5.0])

    cam = CameraView(
        camera_idx=0,
        image_path=img_path,
        rotation=R,
        translation=t,
        intrinsics=K,
        width=200,
        height=200,
    )

    mapper = UVTextureMapper(max_glancing_angle_deg=75.0)
    face_cams, face_uvs = mapper.assign_best_camera_per_triangle(vertices, faces, [cam])

    assert len(face_cams) == 1
    # Camera should be selected for this triangle
    assert face_cams[0] == 0
    # UV coordinates should be within [0, 1]
    assert np.all(face_uvs >= 0.0)
    assert np.all(face_uvs <= 1.0)


def test_bake_and_export_glb(tmp_path):
    vertices = np.array([
        [0.0, 0.0, 0.0],
        [2.0, 0.0, 0.0],
        [0.0, 2.0, 0.0],
    ], dtype=np.float64)
    faces = np.array([[0, 1, 2]], dtype=np.int32)

    img_path = tmp_path / "tex.png"
    Image.new("RGB", (64, 64), color=(200, 100, 50)).save(img_path)

    K = np.array([[50.0, 0.0, 32.0], [0.0, 50.0, 32.0], [0.0, 0.0, 1.0]], dtype=np.float64)
    R = np.eye(3, dtype=np.float64)
    t = np.array([0.0, 0.0, -10.0], dtype=np.float64)

    cam = CameraView(0, img_path, R, t, K, 64, 64)

    out_glb = tmp_path / "textured_output.glb"
    res_path = UVTextureMapper.bake_and_export_glb(vertices, faces, [cam], out_glb)

    assert res_path.exists()
    assert res_path.stat().st_size > 500  # valid non-empty GLB binary
