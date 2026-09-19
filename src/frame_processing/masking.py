"""
Phase 1/2 bridge — converts per-frame UAVid class masks (segmentation.py output) into
COLMAP-compatible dynamic-object masks (ARCHITECTURE.md: "Dynamic classes (Moving car,
Human) -> masked out before reconstruction").

COLMAP's `--ImageReader.mask_path` convention: for image `<name>.jpg`, the mask file is
`<mask_path>/<name>.jpg.png`, same pixel size as the image, 0 = ignore, 255 = keep.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from frame_processing.segmentation import DYNAMIC_CLASSES, UAVID_CLASS_TO_ID

DYNAMIC_CLASS_IDS = {UAVID_CLASS_TO_ID[name] for name in DYNAMIC_CLASSES}


def build_colmap_masks(
    frame_paths: list[str], class_mask_paths: list[str], output_dir: str | Path
) -> list[str]:
    """frame_paths and class_mask_paths must be aligned (same order, same frames).

    Returns the list of written COLMAP mask file paths.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []

    for frame_path, class_mask_path in zip(frame_paths, class_mask_paths):
        class_mask = cv2.imread(class_mask_path, cv2.IMREAD_UNCHANGED)
        if class_mask is None:
            raise IOError(f"Could not read class mask: {class_mask_path}")

        colmap_mask = np.full(class_mask.shape[:2], 255, dtype=np.uint8)
        for dynamic_id in DYNAMIC_CLASS_IDS:
            colmap_mask[class_mask == dynamic_id] = 0

        out_path = output_dir / (Path(frame_path).name + ".png")
        cv2.imwrite(str(out_path), colmap_mask)
        written.append(str(out_path))

    return written
