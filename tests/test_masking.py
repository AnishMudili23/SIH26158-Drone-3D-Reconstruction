"""Regression test for src/frame_processing/masking.py — converts UAVid class masks
into COLMAP's dynamic-object mask convention (0=ignore, 255=use)."""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from frame_processing.masking import build_colmap_masks
from frame_processing.segmentation import UAVID_CLASS_TO_ID


def test_dynamic_classes_are_masked_out(tmp_path):
    class_mask = np.full((20, 20), UAVID_CLASS_TO_ID["Building"], dtype=np.uint8)
    class_mask[5:10, 5:10] = UAVID_CLASS_TO_ID["Moving car"]
    class_mask[12:15, 12:15] = UAVID_CLASS_TO_ID["Human"]
    class_mask_path = tmp_path / "frame_000_mask.png"
    cv2.imwrite(str(class_mask_path), class_mask)

    frame_path = tmp_path / "frame_000.jpg"
    frame_path.touch()

    out_dir = tmp_path / "colmap_masks"
    written = build_colmap_masks([str(frame_path)], [str(class_mask_path)], out_dir)

    colmap_mask = cv2.imread(written[0], cv2.IMREAD_UNCHANGED)
    assert (colmap_mask[5:10, 5:10] == 0).all()   # moving car -> ignored
    assert (colmap_mask[12:15, 12:15] == 0).all()  # human -> ignored
    assert colmap_mask[0, 0] == 255                # building -> kept
    assert Path(written[0]).name == "frame_000.jpg.png"  # COLMAP mask-path convention
