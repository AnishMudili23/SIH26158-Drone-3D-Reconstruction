from pathlib import Path
import numpy as np
import pytest

from src.frame_processing.segmentation import UAVID_CLASS_TO_ID
from src.scene.building_instances import BuildingInstanceExtractor


def test_building_instance_extraction(tmp_path: Path):
    np.random.seed(42)
    bldg_id = UAVID_CLASS_TO_ID["Building"]
    road_id = UAVID_CLASS_TO_ID["Road"]

    # Building 1: 10m x 10m block at (0, 0), z from 0 to 8m (300 points)
    b1_x = np.random.uniform(0, 10, 300)
    b1_y = np.random.uniform(0, 10, 300)
    b1_z = np.random.uniform(0, 8, 300)
    b1_pts = np.column_stack([b1_x, b1_y, b1_z])
    b1_classes = np.full(300, bldg_id, dtype=np.uint8)

    # Road points in between (should not form a building)
    r_x = np.random.uniform(15, 25, 50)
    r_y = np.random.uniform(0, 10, 50)
    r_z = np.full(50, 0.0)
    r_pts = np.column_stack([r_x, r_y, r_z])
    r_classes = np.full(50, road_id, dtype=np.uint8)

    # Building 2: 12m x 15m block at (35, 0), z from 0 to 14m (300 points)
    b2_x = np.random.uniform(35, 47, 300)
    b2_y = np.random.uniform(0, 15, 300)
    b2_z = np.random.uniform(0, 14, 300)
    b2_pts = np.column_stack([b2_x, b2_y, b2_z])
    b2_classes = np.full(300, bldg_id, dtype=np.uint8)

    all_pts = np.vstack([b1_pts, r_pts, b2_pts])
    all_classes = np.concatenate([b1_classes, r_classes, b2_classes])
    confidences = np.full(len(all_pts), 0.92)

    extractor = BuildingInstanceExtractor(dbscan_eps=3.5, dbscan_min_points=20)
    instances = extractor.extract_instances(all_pts, all_classes, confidences)

    # Should separate into 2 discrete buildings
    assert len(instances) == 2

    # Check metrics
    bldg1 = [b for b in instances if b.centroid_xyz[0] < 20][0]
    bldg2 = [b for b in instances if b.centroid_xyz[0] > 25][0]

    assert bldg1.footprint_area_m2 > 50.0
    assert bldg1.height_m > 5.0
    assert bldg1.volume_m3 > 200.0

    assert bldg2.footprint_area_m2 > 100.0
    assert bldg2.height_m > 10.0
    assert bldg2.volume_m3 > 800.0

    # Test saving JSON
    out_json = tmp_path / "buildings.json"
    extractor.save_instances_json(instances, out_json)
    assert out_json.exists()
