import numpy as np
import pytest

from src.frame_processing.segmentation import UAVID_CLASS_TO_ID
from src.scene.ground_detection import MorphologicalGroundDetector


def test_morphological_ground_detection():
    bldg_id = UAVID_CLASS_TO_ID["Building"]
    road_id = UAVID_CLASS_TO_ID["Road"]

    # 1. Flat ground points at z = 0.0
    x_grid, y_grid = np.meshgrid(np.linspace(0, 10, 20), np.linspace(0, 10, 20))
    ground_pts = np.column_stack([x_grid.ravel(), y_grid.ravel(), np.zeros(400)])
    ground_classes = np.full(400, road_id, dtype=np.uint8)

    # 2. Elevated building roof at z = 12.0
    bx, by = np.meshgrid(np.linspace(2, 6, 10), np.linspace(2, 6, 10))
    bldg_pts = np.column_stack([bx.ravel(), by.ravel(), np.full(100, 12.0)])
    bldg_classes = np.full(100, bldg_id, dtype=np.uint8)

    # 3. Vertical facade wall points at x = 2.0, z from 0 to 12
    wall_y, wall_z = np.meshgrid(np.linspace(2, 6, 10), np.linspace(0.5, 11.5, 10))
    wall_pts = np.column_stack([np.full(100, 2.0), wall_y.ravel(), wall_z.ravel()])
    wall_classes = np.full(100, bldg_id, dtype=np.uint8)

    all_pts = np.vstack([ground_pts, bldg_pts, wall_pts])
    all_classes = np.concatenate([ground_classes, bldg_classes, wall_classes])

    detector = MorphologicalGroundDetector(grid_cell_size_m=1.0, height_threshold_m=0.3)
    res = detector.detect_ground(all_pts, all_classes)

    # Ground points should be detected
    assert res.n_ground_points >= 350
    # Building and wall points must NOT be accepted as ground
    assert res.n_rejected_semantic >= 200
    # Ensure all detected ground points are near z=0
    assert np.all(res.ground_points_xyz[:, 2] < 1.0)
