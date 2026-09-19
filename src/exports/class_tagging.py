"""
Phase 7 — Class Tagging: carry per-frame semantic labels (Phase 1) onto point cloud
regions, via nearest-frame projection (ARCHITECTURE.md's "Class Tagging" component).

For each 3D point, project it into every camera that could see it, find the frame(s)
where it lands inside the image bounds with the smallest reprojection depth (i.e. the
frame that most directly observes it), and take that frame's segmentation class at the
projected pixel as the point's class tag. This reuses COLMAP's own per-point track
(which images observe this point) rather than a blind nearest-camera-center heuristic,
so class tags come from a frame that COLMAP itself confirmed actually observes the
point.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from frame_processing.segmentation import UAVID_CLASS_TO_ID  # noqa: E402
from reconstruction.colmap_backend import _camera_intrinsics, _quat_to_rotmat  # noqa: E402

BACKGROUND_ID = UAVID_CLASS_TO_ID["Background clutter"]


def tag_points_by_class(
    points_xyz: np.ndarray,
    point3d_ids: list[int],
    sparse_model: dict,
    masks_dir: str | Path,
) -> np.ndarray:
    """Returns (N,) uint8 array of UAVID_CLASS_TO_ID values, one per input point.

    sparse_model: output of `colmap_backend.read_sparse_text_model()`.
    masks_dir: directory of `<frame_stem>_mask.png` UAVid class masks from
    `frame_processing/segmentation.py`.

    Points with no resolvable track (shouldn't happen for valid COLMAP points) or
    whose observing frames have no mask file default to Background clutter.
    """
    # Build point3D_id -> list of (image_id, point2d_index) from each image's track.
    # COLMAP's images.txt already gives us, per image, the list of (x, y, point3D_id)
    # correspondences — invert that into point3D_id -> [(image_id, x, y), ...].
    point_id_to_observations: dict[int, list[tuple[int, float, float]]] = {}
    for image_id, img_data in sparse_model["images"].items():
        for x, y, pid in img_data["points2d"]:
            point_id_to_observations.setdefault(pid, []).append((image_id, x, y))

    # Cache loaded masks per image so we don't re-read the same file per point.
    mask_cache: dict[int, np.ndarray | None] = {}

    def get_mask(image_id: int) -> np.ndarray | None:
        if image_id in mask_cache:
            return mask_cache[image_id]
        name = sparse_model["images"][image_id]["name"]
        mask_path = Path(masks_dir) / (Path(name).stem + "_mask.png")
        mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED) if mask_path.exists() else None
        mask_cache[image_id] = mask
        return mask

    tags = np.full(len(point3d_ids), BACKGROUND_ID, dtype=np.uint8)
    for i, pid in enumerate(point3d_ids):
        observations = point_id_to_observations.get(pid)
        if not observations:
            continue
        # Use the first observing frame with a readable mask (COLMAP already filtered
        # these to frames that genuinely triangulated this point).
        for image_id, x, y in observations:
            mask = get_mask(image_id)
            if mask is None:
                continue
            xi, yi = int(round(x)), int(round(y))
            if 0 <= yi < mask.shape[0] and 0 <= xi < mask.shape[1]:
                tags[i] = mask[yi, xi]
                break
    return tags


def tags_to_class_names(tags: np.ndarray) -> list[str]:
    id_to_name = {v: k for k, v in UAVID_CLASS_TO_ID.items()}
    return [id_to_name.get(int(t), "Background clutter") for t in tags]
