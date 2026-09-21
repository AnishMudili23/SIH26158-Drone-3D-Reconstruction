from pathlib import Path
import cv2
import numpy as np
import pytest

from src.frame_processing.segmentation import UAVID_CLASS_TO_ID
from src.scene.semantic_voting import MultiViewSemanticVoter


def test_multiview_semantic_voter(tmp_path: Path):
    # Create fake masks for 3 cameras
    masks_dir = tmp_path / "masks"
    masks_dir.mkdir()

    bldg_id = UAVID_CLASS_TO_ID["Building"]
    road_id = UAVID_CLASS_TO_ID["Road"]

    # Cam 1: 100x100 all Building
    m1 = np.full((100, 100), bldg_id, dtype=np.uint8)
    cv2.imwrite(str(masks_dir / "frame_001_mask.png"), m1)

    # Cam 2: 100x100 all Building
    m2 = np.full((100, 100), bldg_id, dtype=np.uint8)
    cv2.imwrite(str(masks_dir / "frame_002_mask.png"), m2)

    # Cam 3: 100x100 with small Road artifact at center
    m3 = np.full((100, 100), bldg_id, dtype=np.uint8)
    m3[45:55, 45:55] = road_id
    cv2.imwrite(str(masks_dir / "frame_003_mask.png"), m3)

    sparse_model = {
        "images": {
            1: {"name": "frame_001.png", "points2d": [(50.0, 50.0, 101)]},
            2: {"name": "frame_002.png", "points2d": [(50.0, 50.0, 101)]},
            3: {"name": "frame_003.png", "points2d": [(50.0, 50.0, 101)]},
        }
    }

    voter = MultiViewSemanticVoter()
    res = voter.vote_points([101], sparse_model, masks_dir)

    # Point 101: 2 Building votes vs 1 Road vote -> Building should win decisively!
    assert len(res.class_ids) == 1
    assert res.class_ids[0] == bldg_id
    assert res.class_names[0] == "Building"
    assert res.observation_counts[0] == 3
    assert res.class_probabilities[0, bldg_id] > 0.50
    assert res.semantic_confidences[0] > 0.30
