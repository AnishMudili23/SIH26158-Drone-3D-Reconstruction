"""
Unit tests for src/exports/las_export.py — ASPRS standard classified point cloud export (.las/.laz).
"""
import sys
from pathlib import Path
import numpy as np
import pytest
import laspy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from exports.las_export import export_point_cloud_to_las, UAVID_TO_ASPRS


def test_export_point_cloud_to_las(tmp_path):
    n_points = 50
    xyz = np.random.uniform(-100, 100, size=(n_points, 3)).astype(np.float64)
    rgb = np.random.randint(0, 256, size=(n_points, 3), dtype=np.uint8)
    uavid_classes = np.random.choice([0, 1, 2, 3, 4, 7], size=n_points).astype(np.uint8)
    confidence = np.random.uniform(0.5, 4.0, size=n_points).astype(np.float32)

    las_file = tmp_path / "test.las"
    result_path = export_point_cloud_to_las(
        points_xyz=xyz,
        output_path=las_file,
        points_rgb=rgb,
        points_class=uavid_classes,
        points_confidence=confidence,
        crs=4326,
    )

    assert result_path.exists()
    assert result_path == las_file

    # Read back using laspy to verify contents
    las = laspy.read(str(las_file))
    assert len(las.points) == n_points
    np.testing.assert_allclose(las.x, xyz[:, 0], atol=1e-3)
    np.testing.assert_allclose(las.y, xyz[:, 1], atol=1e-3)
    np.testing.assert_allclose(las.z, xyz[:, 2], atol=1e-3)

    # Check RGB scaling (8-bit to 16-bit)
    expected_r = (rgb[:, 0].astype(np.uint16) << 8) | rgb[:, 0].astype(np.uint16)
    np.testing.assert_array_equal(las.red, expected_r)

    # Check ASPRS classification mapping
    expected_asprs = np.array([UAVID_TO_ASPRS[c] for c in uavid_classes], dtype=np.uint8)
    np.testing.assert_array_equal(las.classification, expected_asprs)

    # Check CRS VLRs exist
    assert len(las.header.vlrs) > 0


def test_export_point_cloud_to_laz(tmp_path):
    n_points = 20
    xyz = np.ones((n_points, 3), dtype=np.float64) * 42.0

    laz_file = tmp_path / "test.laz"
    result_path = export_point_cloud_to_las(
        points_xyz=xyz,
        output_path=laz_file,
    )

    assert result_path.exists()
    las = laspy.read(str(laz_file))
    assert len(las.points) == n_points
    assert np.all(las.classification == 1)  # Default Unclassified


def test_export_shape_mismatches(tmp_path):
    xyz = np.ones((10, 3))
    wrong_rgb = np.ones((5, 3), dtype=np.uint8)
    out_file = tmp_path / "fail.las"

    with pytest.raises(ValueError, match="points_rgb must match points_xyz length"):
        export_point_cloud_to_las(xyz, out_file, points_rgb=wrong_rgb)
