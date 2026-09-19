"""Regression test for src/exports/class_tagging.py (Phase 7) using a synthetic
sparse-model dict shaped like colmap_backend.read_sparse_text_model()'s output."""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from exports.class_tagging import tag_points_by_class, tags_to_class_names
from frame_processing.segmentation import UAVID_CLASS_TO_ID


def test_tag_points_by_class_reads_correct_pixel(tmp_path):
    # One image, one point observed at pixel (10, 20), where the mask says "Building".
    mask = np.full((50, 50), UAVID_CLASS_TO_ID["Background clutter"], dtype=np.uint8)
    mask[20, 10] = UAVID_CLASS_TO_ID["Building"]
    mask_path = tmp_path / "frame_000_mask.png"
    cv2.imwrite(str(mask_path), mask)

    sparse_model = {
        "images": {
            1: {"name": "frame_000.jpg", "points2d": [(10.0, 20.0, 42)]},
        },
    }
    tags = tag_points_by_class(
        points_xyz=np.zeros((1, 3)), point3d_ids=[42], sparse_model=sparse_model, masks_dir=tmp_path
    )
    assert tags_to_class_names(tags) == ["Building"]


def test_tag_points_defaults_to_background_when_untracked():
    sparse_model = {"images": {}}
    tags = tag_points_by_class(
        points_xyz=np.zeros((2, 3)), point3d_ids=[1, 2], sparse_model=sparse_model, masks_dir="."
    )
    assert tags_to_class_names(tags) == ["Background clutter", "Background clutter"]


def test_tag_points_uses_first_frame_with_readable_mask(tmp_path):
    # Point observed by two frames; only the second frame's mask file exists.
    mask = np.full((50, 50), UAVID_CLASS_TO_ID["Road"], dtype=np.uint8)
    cv2.imwrite(str(tmp_path / "frame_001_mask.png"), mask)

    sparse_model = {
        "images": {
            1: {"name": "frame_000.jpg", "points2d": [(5.0, 5.0, 7)]},
            2: {"name": "frame_001.jpg", "points2d": [(5.0, 5.0, 7)]},
        },
    }
    tags = tag_points_by_class(
        points_xyz=np.zeros((1, 3)), point3d_ids=[7], sparse_model=sparse_model, masks_dir=tmp_path
    )
    assert tags_to_class_names(tags) == ["Road"]
